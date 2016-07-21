#!/usr/bin/env python3


import datetime
import random
import hashlib
from db import *


def _(string):
    return string  # reserved for l10n


def db_err_msg(err):
    return _('Database Error: %s' % str(err))


def check_empty(string):
    return (len(string) == 0)


def now():
    return datetime.datetime.now()


def sha256(string):
    return hashlib.sha256(bytes(string, encoding='utf8')).hexdigest()


def gen_salt():
    result = ''
    for i in range(0, 8):
        result += random.choice('0123456789abcdef')
    return result


def encrypt_password(password, salt):
    return sha256(salt[0:4] + sha256(password) + salt[4:8])


def user_register(mail, user_id, password):
    if(check_empty(mail)):
        return (2, 'Mail address cannot be empty')
    if(check_empty(user_id)):
        return (3, 'User ID cannot be empty')

    try:
        if(User.select().where(User.mail == mail)):
            return (4, _('Mail address already in use.'))
        if(User.select().where(User.user_id == user_id)):
            return (5, _('User ID already in use.'))
    except Exception as err:
        return (1, db_err_msg(err))

    salt = gen_salt()
    encrypted_pw = encrypt_password(password)

    user_rec = User(
        mail = mail,
        user_id = user_id,
        password = encrypted_pw,
        reg_date = now()
    )
    salt_rec = Salt(user=user_rec, salt=salt)

    try:
        user_rec.save()
        salt_rec.save()
    except Exception as err:
        return (1, db_err_msg(err))
    
    return (0, _('User %s registered successfully.' % user_id))


def user_login(login_name, password):
    pass
    #user = None
    #try:
    #    query = User.select().where(User.user_id == login_name)
    #    if(!query):
    #        query = User.select().where(User.mail == login_name)
    #except Exception as err:
    #    return (1, db_err_msg(err))
