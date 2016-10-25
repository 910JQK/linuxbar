#!/usr/bin/env python3


from peewee import *


DEFAULT_SITE_NAME = 'Linuxbar'
DEFAULT_SITE_URL = 'http://127.0.0.1:5000'
DEFAULT_TOPICS_PER_PAGE = '30'
DEFAULT_POSTS_PER_PAGE = '25'
DEFAULT_LIST_ITEM_PER_PAGE = '15'
# in order to position a subpost, fixed value is required
# DEFAULT_SUBPOSTS_PER_PAGE = '10'


# use sqlite temporarily
db = SqliteDatabase('data.db')


class BaseModel(Model):
    class Meta:
        database = db


class Config(BaseModel):
    name = CharField(max_length=64, primary_key=True)
    value = CharField(max_length=255)


class User(BaseModel):
    mail = CharField(max_length=64, unique=True, index=True)
    name = CharField(max_length=32, unique=True, index=True)
    password = FixedCharField(max_length=64) # sha256 with salt
    activated = BooleanField(default=False)
    activation_code = FixedCharField(max_length=16, null=True)
    reg_date = DateTimeField()


class Salt(BaseModel):
    user = ForeignKeyField(User,
                           related_name='salt', primary_key=True, index=True)
    salt = FixedCharField(max_length=8)


class PasswordReset(BaseModel):
    user = ForeignKeyField(User, related_name='password_reset',
                           primary_key=True)
    token = FixedCharField(max_length=64, index=True)
    expire_date = DateTimeField()


class UserInfo(BaseModel):
    user = ForeignKeyField(User, related_name='info', primary_key=True,
                           index=True)
    last_login_date = DateTimeField(null=True)
    last_login_failed_date = DateTimeField(null=True)
    bio = TextField(default='')
    unread_reply = IntegerField(default=0)
    unread_at = IntegerField(default=0)


class Board(BaseModel):
    slug = CharField(max_length=32, unique=True, index=True)
    name = CharField(max_length=64, unique=True)
    description = CharField(255)
    announcement = TextField()
    # TODO: add a sentinel record


class Admin(BaseModel):
    user = ForeignKeyField(User, related_name='admin')
    board = ForeignKeyField(Board, related_name='admin', default=None)
    level = SmallIntegerField(default=0)


class Ban(BaseModel):
    user = ForeignKeyField(User, related_name='banned', index=True)
    operator = ForeignKeyField(User, related_name='banning', index=True)
    board = ForeignKeyField(Board, related_name='banning', index=True,
                            default=None)
    date = DateTimeField(index=True)
    expire_date = DateTimeField()


class DistillateCategory(BaseModel):
    board = ForeignKeyField(Board, related_name='distillate_category', index=True)
    name = CharField(max_length=32)


class Topic(BaseModel):
    title = CharField(max_length=64)
    board = ForeignKeyField(Board, related_name='topics')
    author = ForeignKeyField(User, related_name='topics')
    summary = TextField()
    reply_count = IntegerField(default=0)
    last_post_date = DateTimeField(index=True)
    last_post_author = ForeignKeyField(User)
    pinned = BooleanField(default=False, index=True)
    distillate = BooleanField(default=False, index=True)
    distillate_category = ForeignKeyField(
        DistillateCategory, related_name='topics', null=True,
    )
    deleted = BooleanField(default=False)
    delete_date = DateTimeField(null=True)
    delete_operator = ForeignKeyField(User, 'topics_deleted_by_me', null=True)
    date = DateTimeField()


class Post(BaseModel):
    ordinal = IntegerField()
    content = TextField()
    topic = ForeignKeyField(Topic, related_name='posts')
    topic_author = ForeignKeyField(User) # a post emits a reply to its topic
    author = ForeignKeyField(User, related_name='posts')
    edited = BooleanField(default=False)
    edit_date = DateTimeField(null=True)
    deleted = BooleanField(default=False)
    delete_date = DateTimeField(null=True)
    delete_operator = ForeignKeyField(User, 'posts_deleted_by_me', null=True)
    date = DateTimeField(index=True)


class Subpost(BaseModel):
    ordinal = IntegerField()
    content = TextField()
    author = ForeignKeyField(User, related_name='subposts')
    # a sub-post emits replies both to the post and the topic
    reply0 = ForeignKeyField(Topic, related_name='subposts')
    reply0_author = ForeignKeyField(User, related_name='reply0')
    reply1 = ForeignKeyField(Post, related_name='subposts')
    reply1_author = ForeignKeyField(User, related_name='reply1')
    # a sub-post may emit a reply to another sub-post
    reply2 = ForeignKeyField('self', related_name='replies', null=True)
    reply2_author = ForeignKeyField(User, related_name='reply2', null=True)
    edited = BooleanField(default=False)
    edit_date = DateTimeField(null=True)
    deleted = BooleanField(default=False)
    delete_date = DateTimeField(null=True)
    delete_operator = ForeignKeyField(User, 'subposts_deleted_by_me', null=True)
    date = DateTimeField(index=True)


class AtFromPost(BaseModel):
    post = ForeignKeyField(Post, related_name='At')
    caller = ForeignKeyField(User, related_name='at_from_post_sent')
    callee = ForeignKeyField(User, related_name='at_from_post_received')


class AtFromSubpost(BaseModel):
    subpost = ForeignKeyField(Subpost, related_name='At')
    caller = ForeignKeyField(User, related_name='at_from_subpost_sent')
    callee = ForeignKeyField(User, related_name='at_from_subpost_received')


class Image(BaseModel):
    sha256 = FixedCharField(max_length=64, primary_key=True, index=True)
    uploader = ForeignKeyField(User, related_name='images', index=True)
    file_name = CharField(max_length=256, null=True)
    img_type = CharField(max_length=8)
    date = DateTimeField(index=True)


tables = [Config, User, Salt, PasswordReset, Admin, Board, Ban, BanGlobal,
          Admin, Topic, Post, Subpost, AtFromPost, AtFromSubpost, Image]


if __name__ == '__main__':
    db.connect()

    print('Creating tables ...')
    db.create_tables(tables)
    print('Tables have been created.')

    print('Writing default configurations ...')
    Config.create(name='site_name', value=DEFAULT_SITE_NAME)
    Config.create(name='site_url', value=DEFAULT_SITE_URL)
    Config.create(name='count_topic', value=DEFAULT_TOPICS_PER_PAGE)
    Config.create(name='count_post', value=DEFAULT_POSTS_PER_PAGE)
    Config.create(name='count_list_item', value=DEFAULT_LIST_ITEM_PER_PAGE)
#   Config.create(name='count_subpost', value=DEFAULT_SUBPOSTS_PER_PAGE)
    print('Default configurations have been written into database.')

    db.close()
