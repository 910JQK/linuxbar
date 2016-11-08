from peewee import *
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash


from utils import *
from config import DEFAULT_CONFIG


# use sqlite temporarily
db = SqliteDatabase('data.db')


class Config(BaseModel):
    name = CharField(max_length=64, primary_key=True)
    value = CharField(max_length=255)


class User(UserMixin, BaseModel):
    mail = CharField(max_length=64, unique=True, index=True)
    name = CharField(max_length=32, unique=True, index=True)
    date_register = DateTimeField()
    date_last_login = DateTimeField(null=True)
    date_last_fail = DateTimeField(null=True)
    unread_reply = IntegerField(default=0)
    unread_at = IntegerField(default=0)
    unread_pm = IntegerField(default=0)
    bio = TextField(default='') 
    is_active = BooleanField(default=False)
    activation_token_hash = FixedCharField(max_length=16, null=True)
    def set_activation_token(self, token):
        self.activation_token_hash = sha256(token)
    def activate(self, token):
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


class PasswordResetToken(BaseModel):
    user = ForeignKeyField(User, related_name='password_reset_token',
                           primary_key=True)
    expire_date = DateTimeField()
    token_hash = FixedCharField(max_length=64, index=True)
    def set_token(self, token):
        self.token_hash = sha256(token)
    def check_token(self, token):
        date = now()
        if date < expire_date:
            if self.token_hash == sha256(token):
                return True
            else:
                self.expire_date = date
                self.save()
                return False
        else:
            return False


tables = [Config, User]


def init_db():
    print('Creating tables...')
    db.create_tables(tables)
    print('Writing default configurations...')
    for (name, value) in DEFAULT_CONFIG:
        Config.create(name=name, value=value)
    print('Database initialized successfully.')
