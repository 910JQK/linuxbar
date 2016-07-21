#!/usr/bin/env python3


import datetime
import random
import hashlib
from db import *


def _(string):
    return string  # reserved for l10n


OK_MSG = _('Data retrieved successfully.')


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


def user_register(mail, name, password):
    if(check_empty(mail)):
        return (2, _('Mail address cannot be empty.'))
    if(check_empty(name)):
        return (3, _('User ID cannot be empty.'))
    if(check_empty(password)):
        return (4, _('Password cannot be empty.'))

    try:
        if(User.select().where(User.mail == mail)):
            return (5, _('Mail address already in use.'))
        if(User.select().where(User.name == name)):
            return (6, _('User ID already in use.'))
    except Exception as err:
        return (1, db_err_msg(err))

    salt = gen_salt()
    encrypted_pw = encrypt_password(password, salt)

    try:
        user_rec = User.create(
            mail = mail,
            name = name,
            password = encrypted_pw,
            reg_date = now()
        )
        salt_rec = Salt.create(user=user_rec, salt=salt)
    except Exception as err:
        return (1, db_err_msg(err))

    return (0, _('User %s registered successfully.' % name))


def user_login(login_name, password):
    try:
        query = User.select().where(User.name == login_name)
        if(not query):
            query = User.select().where(User.mail == login_name)
    except Exception as err:
        return (1, db_err_msg(err))

    if(not query):
        return (2, _('No such user.'))
    user = query.get()

    try:
        salt = user.salt[0].salt
    except Exception as err:
        return (1, db_err_msg(err))

    encrypted_pw = encrypt_password(password, salt)
    if(encrypted_pw != user.password):
        return (3, _('Wrong password.'))

    data = {'uid': user.id, 'name': user.name, 'mail': user.mail}
    return (0, _('Login successfully.'), data)


def user_get_uid(name):
    try:
        query = User.select().where(User.name == name)
    except Exception as err:
        return (1, db_err_msg(err))
    if(not query):
        return (2, _('No such user.'))
    user = query.get()
    return (0, OK_MSG, {'uid': user.id})


def site_admin_check(uid):
    try:
        query = User.select().where(User.id == uid)
        if(not query):
            return (2, _('No such user.'))
        user = query.get()
        admin = user.site_managing
    except Exception as err:
        return (1, db_err_msg(err))
    if(admin):
        return (0, OK_MSG, {'site_admin': True})
    else:
        return (0, OK_MSG, {'site_admin': False})


def site_admin_list():
    try:
        query = SiteAdmin.select()
    except Exception as err:
        return (1, db_err_msg(err))
    list = []
    for admin in query:
        list.append(admin.user.id)
    return (0, OK_MSG, {'list': list, 'count': len(list)})


def site_admin_add(uid):
    try:
        query = User.select().where(User.id == uid)

        if(not query):
            return (2, _('No such user.'))
        user = query.get()
        if(user.site_managing):
            return (3, _('User %s is already a site administrator.' % user.name))

        admin = SiteAdmin.create(user=user)
        return (0, _('New site administrator %s added successfully.' % user.name))
    except Exception as err:
        return (1, db_err_msg(err))


def site_admin_remove(uid):
    try:
        query = User.select().where(User.id == uid)
        if(not query):
            return (2, _('No such user'))
        user = query.get()

        query = SiteAdmin.select().where(SiteAdmin.user == user)
        if(not query):
            return (3, _('No such site administrator'))
        admin = query.get()

        admin.delete_instance()
        return (0, _('Site administrator %s removed successfully.' % user.name))
    except Exception as err:
        return (1, db_err_msg(err))


def board_list():
    try:
        query = Board.select()
    except Exception as err:
        return (1, db_err_msg(err))
    list = []
    for board in query:
        list.append({
            'bid': board.id,
            'short_name': board.short_name,
            'name': board.name,
            'desc': board.description,
            'announce': board.announcement
        })
    return (0, OK_MSG, {'list': list, 'count': len(list)})


def board_add(short_name, name, desc, announce):
    if(check_empty(short_name)):
        return (2, _('Board ID (short name) cannot be empty'))
    if(check_empty(name)):
        return (3, _('Board name cannot be empty'))
    try:
        if(Board.select().where(Board.short_name == short_name)):
            return (4, _('Board with ID (short name) %s already exists.'
                         % short_name))
        Board.create(
            short_name = short_name,
            name = name,
            description = desc,
            announcement = announce
        )
        return (0, _('Board named %s created successfully.' % name))
    except Exception as err:
        return (1, db_err_msg(err))


def board_remove(short_name):
    try:
        query = Board.select().where(Board.short_name == short_name)
        if(not query):
            return (2, _('No such board'))
        board = query.get()
        board.delete_instance()
        return (0, _('Board named %s removed successfully.' % board.name))
    except Exception as err:
        return (1, db_err_msg(err))


#def board_update(short_name
