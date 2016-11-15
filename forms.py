from flask_wtf import FlaskForm
from wtforms import *
from wtforms.validators import *


from utils import _
from validation import *
from config import TOKEN_LIFETIME
from captcha import CAPTCHA_REGEX


def Required():
    return InputRequired(_('This field is required.'))


def Username():
    return Regexp(REGEX_USERNAME, message=_('Invalid username format.'))


def PasswordConfirm():
    return EqualTo('password', message=_('Passwords are inconsistent.'))


class RegisterForm(FlaskForm):
    mail = StringField(
        _('Email Address'),
        validators = [
            Required(), Email(_('Invalid Email Address.')), SizeRange(3, 64)
        ],
        description = _('Used to enable your account and reset your password.')
    )
    name = StringField(
        _('Nickname'),
        validators = [
            Required(), Username()
        ],
        description = _('Nickname as well as identifier.')
    )
    password = PasswordField(
        _('Password'),
        validators = [
            Required()
        ],
        description = _("Your password. Won't be encrypted if not using HTTPS.")
    )
    confirm = PasswordField(
        _('Password Confirmation'),
        validators = [
            PasswordConfirm()
        ],
        description = _('Repeat your password to confirm.')
    )
    captcha = StringField(
        _('Captcha'),
        validators = [
            Required(), Regexp(CAPTCHA_REGEX, message=_('Invalid captcha'))
        ],
        description = 'Input the text on the image.'
    )


class LoginForm(FlaskForm):
    login_name = StringField(
        _('Login name'),
        validators = [
            Required(), SizeRange(3, 64)
        ],
        description = _('Login Name can be either nickname or email address.')
    )
    password = PasswordField(
        _('Password'),
        validators = [
            Required()
        ],
        description = _("Your password. Won't be encrypted if not using HTTPS.")
    )
    remember_me = BooleanField(
        _('Remember me')
    )


class GetTokenForm(FlaskForm):
    mail = StringField(
        _('Email Address'),
        validators = [
            Required(), Email(_('Invalid Email Address.'))
        ],
        description = _('Email address of your account.')
    )


class PasswordResetForm(FlaskForm):    
    password = PasswordField(
        _('New Password'),
        validators = [
            Required()
        ],
        description = _("New password. Won't be encrypted if not using HTTPS.")
    )
    confirm = PasswordField(
        _('Password Confirmation'),
        validators = [
            PasswordConfirm()
        ],
        description = _('Repeat your password to confirm.')
    )
    token = StringField(
        _('Token'),
        validators = [
            Regexp(REGEX_TOKEN, message=_('Invalid token format'))
        ],
        description = (
            _('The token sent to you by email. Valid in %d minutes.')
            % TOKEN_LIFETIME
        )
    )


class UserConfigForm(FlaskForm):
    view_nested = BooleanField(_('Show nested tree structure of posts'))
    view_expanded = BooleanField(_('Expand all the tree structure of posts'))
    bio = TextAreaField(_('Bio'), description=_('A brief description of you.'))
