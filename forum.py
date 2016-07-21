#!/usr/bin/env python3


import datetime
import random
import hashlib
from db import *


def _(string):
    return string  # reserved for l10n


def err_msg(err):
    return _('Internal Error:') + str(err)


def now():
    return datetime.datetime.now()


def sha256(string):
    return hashlib.sha256(bytes(string, encoding='utf8')).hexdigest()


def gen_salt():
    result = ''
    for i in range(0, 8):
        result += random.choice('0123456789abcdef')
    return result


def user_register(mail, user_id, password):
    if(User.select().where(User.mail == mail)):
        return (2, _('Mail address already in use.'))
    if(User.select().where(User.user_id == user_id)):
        return (3, _('User ID already in use.'))

    salt = gen_salt()
    password_encrypted = sha256(salt[0:4] + sha256(password) + salt[4:8])

    user_rec = User(
        mail=mail,
        user_id=user_id,
        password=password_encrypted,
        reg_date = now()
    )
    salt_rec = Salt(user=user_rec, salt=salt)

    try:
        user_rec.save()
        salt_rec.save()
    except Exception as err:
        return (1, err_msg(err))
    
    return (0, _('User %s registered successfully.' % user_id))
