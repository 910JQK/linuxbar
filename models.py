import datetime
from peewee import *
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash


from utils import *
from config import DEFAULT_CONFIG, TOKEN_LIFETIME


# use sqlite temporarily
db = SqliteDatabase('data.db')


class BaseModel(Model):
    class Meta:
        database = db


class Config(BaseModel):
    name = CharField(max_length=64, primary_key=True)
    value = CharField(max_length=255)
    @classmethod
    def Get(Config, name):
        return Config.get(Config.name == name).value


class User(UserMixin, BaseModel):
    mail = CharField(max_length=64, unique=True, index=True)
    name = CharField(max_length=32, unique=True, index=True)
    date_register = DateTimeField()
    date_last_login = DateTimeField(null=True)
    date_last_fail = DateTimeField(null=True)
    unread_reply = IntegerField(default=0)
    unread_at = IntegerField(default=0)
    unread_pm = IntegerField(default=0)
    admin_level = SmallIntegerField(default=0)
    is_active = BooleanField(default=False)
    activation_token_hash = FixedCharField(max_length=16, null=True)
    def set_activation_token(self, token):
        self.activation_token_hash = sha256(token)
    def activate(self, token):
        if self.is_active:
            return True
        if self.activation_token_hash == sha256(token):
            self.activation_token_hash = None
            self.is_active = True
            self.save()
            return True
        else:
            self.activation_token_hash = None
            self.save()
            return False
    password_hash = FixedCharField(max_length=64)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class UserConfig(BaseModel):
    user = ForeignKeyField(User, related_name='config', primary_key=True)
    view_nested = BooleanField(default=True)
    view_expanded = BooleanField(default=True)


class Profile(BaseModel):
    user = ForeignKeyField(User, related_name='profile', primary_key=True)
    bio = TextField(null=True)
    location = CharField(max_length=64, null=True)
    birth_year = SmallIntegerField(null=True)
    occupation = CharField(max_length=32, null=True)
    im_accounts = CharField(max_length=128, null=True)


class PasswordResetToken(BaseModel):
    user = ForeignKeyField(User, related_name='password_reset_token',
                           primary_key=True)
    expire_date = DateTimeField()
    token_hash = FixedCharField(max_length=64, index=True)
    def set_token(self, token):
        self.expire_date = now() + datetime.timedelta(minutes=TOKEN_LIFETIME)
        self.token_hash = sha256(token)
    def check_token(self, token):
        date = now()
        if date < self.expire_date:
            self.expire_date = date
            self.save()
            if self.token_hash == sha256(token):
                return True
            else:
                return False
        else:
            return False


class Ban(BaseModel):
    user = ForeignKeyField(User, related_name='banned', unique=True)
    operator = ForeignKeyField(User, related_name='banning')
    date = DateTimeField()
    days = SmallIntegerField(default=1)
    def is_valid(self):
        return (
            now() < self.date + datetime.timedelta(days=self.days)
        )
    @classmethod
    def try_to_create(Ban, user, days, operator):
        query = Ban.select().where(Ban.user == user)
        if query:
            ban = query.get()
            if ban.is_valid() and ban.days > days:
                return False
            else:
                ban.date = now()
                ban.days = days
                ban.operator_id = operator.id
                ban.save()
                return True
        else:
            Ban.create(
                user = user,
                date = now(),
                days = days,
                operator_id = operator.id
            )
            return True


class Tag(BaseModel):
    slug = CharField(max_length=32, unique=True, index=True)
    name = CharField(max_length=64, unique=True)
    description = CharField(255)


class Topic(BaseModel):
    author = ForeignKeyField(User, related_name='topics')
    title = CharField(max_length=64)
    summary = CharField(max_length=255)
    post_date = DateTimeField()
    reply_count = IntegerField(default=0)
    last_reply_date = DateTimeField()
    last_reply_author = ForeignKeyField(User)
    is_pinned = BooleanField(default=False, index=True)
    is_distillate = BooleanField(default=False, index=True)
    is_deleted = BooleanField(default=False, index=True)


class TagRelation(BaseModel):
    topic = ForeignKeyField(Topic, related_name='tags')
    tag = ForeignKeyField(Tag, related_name='topics')


class Post(BaseModel):
    topic = ForeignKeyField(Topic, related_name='posts', null=True)
    topic_author = ForeignKeyField(User)
    ordinal = IntegerField()
    content = TextField()
    date = DateTimeField()
    last_edit_date = DateTimeField(null=True)
    author = ForeignKeyField(User, related_name='posts')
    path = TextField(default='/')
    is_deleted = BooleanField(default=False)


class DeleteRecord(BaseModel):
    topic = ForeignKeyField(Topic, related_name='delete_record', null=True)
    post = ForeignKeyField(Post, related_name='delete_record', null=True)
    is_revert = BooleanField(default=False)
    date = DateTimeField()
    operator = ForeignKeyField(User, related_name='del_rec_topic')


class Message(BaseModel):
    post = ForeignKeyField(Post, related_name='msg')
    caller = ForeignKeyField(User, related_name='msg_calling')
    callee = ForeignKeyField(User, related_name='msg_called')
    is_system_message = BooleanField(default=False)


class Image(BaseModel):
    sha256 = FixedCharField(max_length=64, primary_key=True, index=True)
    uploader = ForeignKeyField(User, related_name='images', index=True)
    file_name = CharField(max_length=256, null=True)
    img_type = CharField(max_length=8)
    date = DateTimeField(index=True)


tables = [
    Config, User, UserConfig, Profile, PasswordResetToken, Ban,
    Tag, Topic, TagRelation, Post,
    DeleteRecord, Message, Image
]


def init_db():
    print('Creating tables...')
    db.create_tables(tables)
    print('Writing default configurations...')
    for (name, value) in DEFAULT_CONFIG.items():
        Config.create(name=name, value=value)
    print('Database initialized successfully.')
