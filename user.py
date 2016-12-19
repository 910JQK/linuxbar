from flask import Blueprint, session, request, flash, redirect, render_template, url_for, abort
from flask_login import (
    LoginManager, current_user, login_required, login_user, logout_user
)


from utils import _
from utils import *
from config import DB_WILDCARD
from validation import REGEX_TOKEN
from post import create_system_message
from forms import (
    LoginForm,
    RegisterForm,
    GetTokenForm,
    PasswordResetForm,
    ProfileForm,
    BanForm,
    LevelChangeForm
)
from models import (
    Config, User, PasswordResetToken, Profile, Ban,
    Message, Post, Topic
)


user = Blueprint(
    'user', __name__, template_folder='templates', static_folder='static'
)


login_manager = LoginManager()
login_manager.login_view = 'user.login'
login_manager.login_message = _('Please sign in to access this page.')
login_manager.REMEMBER_COOKIE_HTTPONLY = True


@login_manager.user_loader
def load_user(uid):
    return User.get(User.id == int(uid))


def privilege_required(admin=False):
    def decorator(f):
        def wrapper(*args, **kwargs):
            if current_user.is_authenticated:
                if (
                        (admin and current_user.level == 2)
                        or (not admin and current_user.level != 0)
                ):
                    return f(*args, **kwargs)
                else:
                    abort(401)
            else:
                flash(login_manager.login_message)
                return redirect(url_for('.login'))
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator


def send_token_activation(user, token):
    url = (
        Config.Get('site_url') + url_for('.activate', uid=user.id, token=token)
    )
    send_mail(
        subject = _('Activation Mail - %s') % Config.Get('site_name'),
        addr_from = Config.Get('mail_addr'),
        addr_to = user.mail,
        content = _('Activation link for %s: ') % user.name + url,
        html = _(
            ('Activation link for %s: ') % user.name
            + '<a target="_blank" href="%s">%s</a>' % (
                url_quote(url),
                escape(url)
            )
        )
    )


def send_token_password_reset(user, token):
    send_mail(
        subject = (
            _('Reset Password for %s - %s')
            % (user.name, Config.Get('site_name'))
        ),
        addr_from = Config.Get('mail_addr'),
        addr_to = user.mail,
        content = _('Your token is: %s') % token
    )


@user.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    signed_up = False
    if form.validate_on_submit():
        if session.get('captcha') == form.captcha.data:
            conflict = User.select().where(
                User.mail == form.mail.data
                | User.name == form.name.data
            )
            if not conflict:
                user = User(
                    mail = form.mail.data,
                    name = form.name.data,
                    date_register = now()
                )
                token = gen_token()
                user.set_activation_token(token)
                user.set_password(form.password.data)
                user.save()
                Profile.create(user=user)
                send_token_activation(user, token)
                flash(_('Signed up successfully. Activation mail has been sent to you. Please login after activation.'), 'ok')
                signed_up = True
            else:
                if conflict.mail == form.mail.data:
                    flash(_('Email address already in use.'), 'err')
                else:
                    flash(_('Name already in use.'), 'err')
        else:
            flash(_('Wrong captcha.'), 'err')
    return render_template('user/register.html', form=form, signed_up=signed_up)


@user.route('/activate/<int:uid>/<token>')
def activate(uid, token):
    if REGEX_TOKEN.fullmatch(token):
        user = find_record(User, id=uid)
        if user:
            if user.activate(token):
                flash(_('User %s activated successfully.') % user.name, 'ok')
                return redirect(url_for('.login'))
            else:
                flash(_('Wrong activation token.'), 'err')
        else:
            flash(_('No such user.'), 'err')
    else:
        flash(_('Wrong token format.'), 'err')
    return redirect(url_for('index'))


@user.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash(_('You have already signed in.'))
        return redirect('index')
    form = LoginForm()
    if form.validate_on_submit():
        query = User.select().where(
            (User.mail == form.login_name.data)
            | (User.name == form.login_name.data)
        )
        user = bool(query) and query.get()
        if user and user.check_password(form.password.data):
            if login_user(user, form.remember_me.data):
                user.date_last_login = now()
                user.save()
                flash(_('Signed in successfully.'), 'ok')
                return redirect(request.args.get('next') or url_for('index'))
            else:
                flash(_('This user is inactive.'), 'err')
        else:
            if user:
                user.date_last_fail = now()
                user.save()
            flash(_('Invalid login name or password.'), 'err')
    return render_template('user/login.html', form=form)


@user.route('/get-token', methods=['GET', 'POST'])
def get_token():
    form = GetTokenForm()
    if form.validate_on_submit():
        mail = form.mail.data
        user = find_record(User, mail=mail)
        if user:
            old_token_record = find_record(PasswordResetToken, user=user)
            if not old_token_record or old_token_record.expire_date < now():
                token = gen_token()
                token_record = (
                    old_token_record or PasswordResetToken(user=user)
                )
                token_record.set_token(token)
                if old_token_record:
                    token_record.save()
                else:
                    token_record.save(force_insert=True)
                send_token_password_reset(user, token)
                return redirect(url_for('.password_reset', uid=user.id))
            else:
                flash(_('A valid token has already been sent to you.'), 'err')
        else:
            flash(_('No such user.'), 'err')
    return render_template('user/get_token.html', form=form)


@user.route('/password-reset/<int:uid>', methods=['GET', 'POST'])
def password_reset(uid):
    form = PasswordResetForm()
    if form.validate_on_submit():
        token = form.token.data
        user = find_record(User, id=uid)
        if user:
            token_record = find_record(PasswordResetToken, user=user)
            if token_record and token_record.check_token(token):
                user.set_password(form.password.data)
                user.save()
                flash(_('Password reset successfully.'), 'ok')
                return redirect(url_for('.login'))
            else:
                flash(_('Invalid token.'), 'err')
        else:
            flash(_('No such user.'), 'err')
    return render_template('user/password_reset.html', form=form)


@user.route('/profile/<int:uid>')
def profile(uid):
    user = find_record(User, id=uid)
    if user:
        return render_template(
            'user/profile.html',
            user = user,
            profile = user.profile[0]
        )
    else:
        abort(404)


@user.route('/profile/name/<name>')
def profile_by_name(name):
    user = find_record(User, name=name)
    if user:
        return redirect(url_for('.profile', uid=user.id))
    else:
        abort(404)


@user.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def profile_edit():
    profile = current_user.profile[0]
    form = ProfileForm(obj=profile)
    if form.validate_on_submit():
        form.populate_obj(profile)
        profile.save()
        flash(_('Profile updated successfully.'), 'ok')
        return redirect(url_for('.profile', uid=current_user.id))
    return render_template('user/profile_edit.html', form=form)


@user.route('/ban/<int:uid>', methods=['GET', 'POST'])
@privilege_required()
def ban(uid):
    user = find_record(User, id=uid)
    if user:
        ok = False
        form = BanForm()
        if form.validate_on_submit():
            if Ban.try_to_create(user, int(form.days.data), current_user):
                flash(
                    _('Ban on user %s entered into force.') % user.name,
                    'ok'
                )
                ok = True
                create_system_message(
                    (
                        _('You have been banned by moderator {0} for {1} days.')
                        .format(current_user.name, form.days.data)
                    ),
                    user
                )
            else:
                flash(_('A ban with longer duration already exists.'), 'err')
        return render_template('user/ban.html', user=user, form=form, ok=ok)
    else:
        abort(404)


@user.route('/change-level/<int:uid>', methods=['GET', 'POST'])
@privilege_required(admin=True)
def change_level(uid):
    user = find_record(User, id=uid)
    if user:
        form = LevelChangeForm(obj=user)
        if form.validate_on_submit():
            if user.id != current_user.id and user.level == 2:
                flash(_('Invalid operation.'), 'err')
            else:
                form.populate_obj(user)
                user.save()
                flash(_('User privilege changed successfully.'), 'ok')
            return redirect(url_for('.profile', uid=uid))
        return render_template('user/change_level.html', form=form, user=user)
    else:
        abort(404)


@user.route('/logout')
@login_required
def logout():
    logout_user()
    flash(_('Signed out successfully.'), 'ok')
    return redirect(request.args.get('next') or url_for('index'))


@user.route('/notifications/<n_type>')
@login_required
def notifications(n_type):
    if n_type not in ['reply', 'at', 'sys']:
        abort(404)
    user = find_record(User, id=current_user.id)
    if n_type == 'reply':
        (
            User
            .update(unread_reply = 0)
            .where(User.id == user.id)
        ).execute()
        current_user.unread_reply = 0
    elif n_type == 'at':
        (
            User
            .update(unread_at = 0)
            .where(User.id == user.id)
        ).execute()
        current_user.unread_at = 0
    elif n_type == 'sys':
        (
            User
            .update(unread_sys = 0)
            .where(User.id == user.id)
        ).execute()
        current_user.unread_sys = 0
    pn = int(request.args.get('pn', '1'))
    count = int(Config.Get('count_item'))
    if n_type != 'sys':
        messages = (
            Message
            .select(Message, User, Post, Topic)
            .join(User)
            .switch(Message)
            .join(Post)
            .join(Topic)
            .where(
                Message.msg_type == n_type,
                Message.callee == user
            )
        )
    else:
        messages = (
            Message.select(Message, Post)
            .join(Post)
            .where(
                Message.msg_type == n_type,
                Message.callee == user
            )
        )
    total = messages.count()
    message_list = messages.order_by(Post.date.desc()).paginate(pn, count)
    return render_template(
        'user/notification.html',
        n_type = n_type,
        pn = pn,
        count = count,
        total = total,
        message_list = message_list
    )
