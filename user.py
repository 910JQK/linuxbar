from flask import Blueprint, session, request, flash, redirect, render_template, url_for, abort
from flask_login import (
    LoginManager, current_user, login_required, login_user, logout_user
)


from utils import _
from utils import *
from validation import REGEX_TOKEN
from forms import (
    LoginForm,
    RegisterForm,
    GetTokenForm,
    PasswordResetForm,
    UserConfigForm,
    ProfileForm,
    BanForm
)
from models import Config, User, PasswordResetToken, UserConfig, Profile, Ban


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


def admin_required(f, *args, **kwargs):
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated:
            if current_user.admin_level > 0:
                return f(*args, **kwargs)
            else:
                abort(401)
        else:
            flash(login_manager.login_message)
            return redirect(url_for('.login'))
    return wrapper


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
                UserConfig.create(user=user)
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


@user.route('/config', methods=['GET', 'POST'])
@login_required
def config():
    user_config = current_user.config[0]
    form = UserConfigForm(obj=user_config)
    if form.validate_on_submit():
        form.populate_obj(user_config)
        user_config.save()
        flash(_('Configurations updated successfully.'), 'ok')
    return render_template('user/config.html', form=form)


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


@user.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def profile_edit():
    profile = current_user.profile[0]
    form = ProfileForm(obj=profile)
    if form.validate_on_submit():
        form.populate_obj(profile)
        profile.save()
        flash(_('Profile updated successfully.'), 'ok')
    return render_template('user/profile_edit.html', form=form)


@user.route('/ban/<int:uid>', methods=['GET', 'POST'])
@admin_required
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
            else:
                flash(_('A ban with longer duration already exists.'), 'err')
        return render_template('user/ban.html', user=user, form=form, ok=ok)
    else:
        abort(404)


@user.route('/logout')
@login_required
def logout():
    logout_user()
    flash(_('Signed out successfully.'), 'ok')
    return redirect(url_for('index'))
