#!/usr/bin/env python3


from peewee import *


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
    reg_date = DateTimeField()


class Salt(BaseModel):
    user = ForeignKeyField(User,
                           related_name='salt', primary_key=True, index=True)
    salt = FixedCharField(max_length=8)


class SiteAdmin(BaseModel):
    user = ForeignKeyField(User, related_name='site_managing', primary_key=True)


class Board(BaseModel):
    short_name = CharField(max_length=32, unique=True, index=True)
    name = CharField(max_length=64, unique=True)
    description = CharField(255)
    announcement = TextField()


class Ban(BaseModel):
    user = ForeignKeyField(User, related_name='banned', unique=True, index=True)
    operator = ForeignKeyField(User, related_name='banning', index=True)
    board = ForeignKeyField(Board, related_name='banning', index=True)
    date = DateTimeField(index=True)
    expire_date = DateTimeField()


class BanGlobal(BaseModel):
    user = ForeignKeyField(User, related_name='banned_global', unique=True,
                           index=True)
    operator = ForeignKeyField(User, related_name='banning_global', index=True)
    date = DateTimeField(index=True)
    expire_date = DateTimeField()


class BoardAdmin(BaseModel):
    user = ForeignKeyField(User, related_name='board_managing')
    board = ForeignKeyField(Board, related_name='admin')
    level = SmallIntegerField(default=0)


class Topic(BaseModel):
    title = CharField(max_length=64)
    board = ForeignKeyField(Board, related_name='topics')
    author = ForeignKeyField(User, related_name='topics')
    last_post_date = DateTimeField(index=True)
    last_post_author = ForeignKeyField(User)
    deleted = BooleanField(default=False)
    delete_date = DateTimeField(null=True)
    delete_operator = ForeignKeyField(User, 'topics_deleted_by_me', null=True)
    date = DateTimeField()


class Post(BaseModel):
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


tables = [Config, User, Salt, SiteAdmin, Board, Ban, BanGlobal, BoardAdmin,
          Topic, Post, Subpost, AtFromPost, AtFromSubpost, Image]


if __name__ == '__main__':
    db.connect()
    print('Creating tables ...')
    db.create_tables(tables)
    print('Tables have been created.')
    db.close()
