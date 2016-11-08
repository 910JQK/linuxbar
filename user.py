from flask import Blueprint, request, flash, redirect, render_template, url_for, abort
from flask_login import (
    LoginManager, current_user, login_required, login_user, logout_user
)


from utils import _
from utils import *
from validation import REGEX_TOKEN
from forms import LoginForm
from models import Config, User


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


def send_token_reset_password(user, token):
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
                user.save()
                send_token_activation(user, token)
                flash(_('Signed up successfully'))
                redirect(url_for('.login'))
            else:
                if conflict.mail == form.mail.data:
                    flash(_('Email address already in use.'))
                else:
                    flash(_('Name already in use.'))
        else:
            flash(_('Wrong captcha.'))
    return render_template('user/register.html', form=form)


@user.route('/activate/<int:uid>/<token>')
def activate(uid, token):
    if REGEX_TOKEN.fullmatch(token):
        user = find_record(User, id=uid)
        if user:
            if user.activate(token):
                flash(_('User %s activated successfully.') % user.name)
                return redirect(url_for('.login'))
            else:
                flash(_('Wrong activation token.'))
        else:
            flash(_('No such user.'))
    else:
        flash(_('Wrong token format.'))
    return redirect(url_for('index'))


@user.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        query = User.select().where(
            User.mail == form.login_name.data
            | User.name == form.login_name.data
        )
        if query and query.get().check_password(form.password.data):
            login_user(query.get(), form.remember_me.data)
            flash(_('Signed in successfully.'))
            return redirect(request.args.get('next') or url_for('index'))
        else:
            flash(_('Invalid login name or password.'))
    return render_template('user/login.html', form=form)


@user.route('/get-token', methods=['GET', 'POST'])
def get_token():
    form = GetTokenForm()
    if form.validate_on_submit():
        mail = form.mail.data
        user = find_record(User, mail=mail)
        if user:
            token = gen_token()
            token_record = PasswordResetToken(user=user)
            token_record.set_token(token)
            token_record.save()
            send_token_password_reset(user, token)
            return redirect(url_for('.password_reset', uid=user.uid))
        else:
            flash(_('No such user.'))
    return render_template('render/get_token.html', form=form)


@user.route('/password-reset/<int:uid>', methods=['GET', 'POST'])
def password_reset(uid):
    form = PasswordResetForm()
    if form.validate_on_submit():
        user = find_record(User, id=uid)
        if user:
            token_record = find_record(PasswordResetToken, user=user)
            if token_record and token_record.check_token(token):
                user.set_password(form.password.data)
                flash(_('Password reset successfully.'))
                return redirect(url_for('.login'))
            else:
                flash(_('Invalid token.'))
        else:
            flash(_('No such user.'))
    return render_template('user/password_reset.html', uid=uid, form=form)


@user.route('/logout')
@login_required
def logout():
    logout_user()
    flash(_('Signed out successfully.'))
    return redirect(url_for('index'))
