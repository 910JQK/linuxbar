from wtforms import *
from wtforms.validators import *
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired


from utils import _
from validation import *
from config import TOKEN_LIFETIME, BAN_DAYS
from captcha import CAPTCHA_REGEX


def ConfigField(name, description, *validators):
    return StringField(
        name,
        validators = [Required(), SizeRange(1, 256), *validators],
        description = description
    )


def Required():
    return InputRequired(_('This field is required.'))


def Username():
    def validator(form, field):
        if not REGEX_USERNAME.fullmatch(field.data):
            raise ValidationError(_('Invalid username format.'))
    return validator


def PasswordConfirm():
    return EqualTo('password', message=_('Passwords are inconsistent.'))


def PositiveInteger():
    return Regexp(REGEX_PINT, message=_('Positive integer required'))


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


class ProfileForm(FlaskForm):
    bio = TextAreaField(_('Bio'), description=_('A brief description of you.'))
    location = StringField(
        _('Location'),
        validators = [Optional(), SizeRange(1, 64)],
        description = _('Your geolocation.')
    )
    birth_year = IntegerField(
        _('Birth Year'),
        validators = [Optional(), NumberRange(min=1000)],
        description = _('Your birth year, at least four digits.')
    )
    occupation = StringField(
        _('Occupation'),
        validators = [Optional(), SizeRange(1, 32)],
        description = _('Your work.')
    )
    im_accounts = StringField(
        _('IM Accounts'),
        validators = [Optional(), SizeRange(1, 256)],
        description = _('Your instant-messaging accounts.')
    )


class BanForm(FlaskForm):
    days = SelectField(
        _('Duration'),
        choices = [
            (
                str(days),
                _('%d Day', '%d Days', days) % days
            )
            for days in BAN_DAYS
        ],
        coerce = str
    )


class LevelChangeForm(FlaskForm):
    level = SelectField(
        _('Privilege'),
        choices = [
            (0, _('None')), (1, _('Moderator')), (2, _('Administrator'))
        ],
        coerce = int
    )


class ConfigEditForm(FlaskForm):
    site_name = ConfigField(
        _('Site Name'),
        _('Name of this site.')
    )
    site_url = ConfigField(
        _('Site URL'),
        _('URL of this site. Example: https://foobar.invalid')
    )
    mail_addr = ConfigField(
        _('Email Address'),
        _('Email address showed in mails sent by this site.')
    )
    count_topic = ConfigField(
        _('Topics per page'),
        _('The number of topics shown in one page in a topic list.'),
        PositiveInteger()
    )
    count_post = ConfigField(
        _('Posts per page'),
        _('The number of posts shown in one page in a post list.'),
        PositiveInteger()
    )
    count_item = ConfigField(
        _('Items per page'),
        _('The number of items shown in one page in a list'),
        PositiveInteger()
    )


class TagEditForm(FlaskForm):
    slug = StringField(
        _('Slug'),
        validators = [
            Required(),
            SizeRange(1, 32),
            Regexp(REGEX_SLUG, message=_('Invalid format.'))
        ],
        description = _('Name in URL. Only Latin, number and "-" are allowed.')
    )
    name = StringField(
        _('Name'),
        validators = [Required(), SizeRange(1, 64)],
        description = _('Name that is displayed.')
    )
    description = TextAreaField(
        _('Description'),
        validators = [Required(), SizeRange(1, 256)],
        description = _('Detailed description.')
    )


class ImageUploadForm(FlaskForm):
    image = FileField(
        _('Image'),
        validators = [FileRequired()],
        description = _('Image file to upload (PNG/JPG/GIF).')
    )


class TopicAddForm(FlaskForm):
    # size range of the title must be consistent with the front-end script
    title = StringField(_('Title'), validators=[Required(), SizeRange(1, 64)])
    content = TextAreaField(
        _('Content'), validators=[Required(), SizeRange(1, 15000)]
    )
    tags = SelectMultipleField(_('Tags'), validators=[Optional()], coerce=str)


class PostAddForm(FlaskForm):
    content = TextAreaField(
        _('Content'), validators=[Required(), SizeRange(1, 15000)]
    )


class TopicTagManageForm(FlaskForm):
    tags = SelectMultipleField(_('Tags'), validators=[Optional()], coerce=str)


class FaceAddForm(FlaskForm):
    name = StringField(
        _('Name'),
        validators = [
            Required(),
            SizeRange(1, 32)
        ],
        description = _('Name of the face.')
    )
    hash_value = StringField(
        _('Hash'),
        validators = [
            Required(),
            Regexp(REGEX_SHA256_PART, message=_('Invalid format'))
        ],
        description = _('Image hash value.')
    )
