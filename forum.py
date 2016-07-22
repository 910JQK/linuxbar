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


def user_get_name(uid):
    try:
        query = User.select().where(User.id == uid)
    except Exception as err:
        return (1, db_err_msg(err))
    if(not query):
        return (2, _('No such user.'))
    user = query.get()
    return (0, OK_MSG, {'name': user.name})


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
            return (2, _('No such user.'))
        user = query.get()

        query = SiteAdmin.select().where(SiteAdmin.user == user)
        if(not query):
            return (3, _('No such site administrator.'))
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
        return (2, _('Board ID (short name) cannot be empty.'))
    if(check_empty(name)):
        return (3, _('Board name cannot be empty.'))
    try:
        if(Board.select().where(Board.short_name == short_name)):
            return (4, _('Board with ID (short name) %s already exists.'
                         % short_name))
        if(Board.select().where(Board.name == name)):
            return (5, _('Board named %s already exists.' % name))
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
    # regard short name as ID for convenience
    try:
        query = Board.select().where(Board.short_name == short_name)
        if(not query):
            return (2, _('No such board.'))
        board = query.get()
        board.delete_instance()
        return (0, _('Board named %s removed successfully.' % board.name))
    except Exception as err:
        return (1, db_err_msg(err))


def board_update(original_short_name, short_name, name, desc, announce):
    # regard short name as ID for convenience
    try:
        query = Board.select().where(Board.short_name == original_short_name)
        if(not query):
            return (2, _('No such board.'))
        board = query.get()
        board.short_name = short_name
        board.name = name
        board.description = desc
        board.announcement = announce
        board.save()
        return (0, _('Info of board named %s updated successfully.' % name))
    except Exception as err:
        return(1, db_err_msg(err))


def ban_global_check(uid):
    try:
        query = User.select().where(User.id == uid)
        if(not query):
            return (2, _('No such user.'))
        user = query.get()
        banned = user.banned_global
    except Exception as err:
        return (1, db_err_msg(err))
    if(banned and now() < banned[0].expire_date):
        return (0, OK_MSG, {
            'banned': True,
            'expire_date': banned[0].expire_date
        })
    else:
        return (0, OK_MSG, {'banned': False})


def ban_global_info(uid):
    try:
        query = User.select().where(User.id == uid)
        if(not query):
            return (2, _('No such user.'))
        user = query.get()
        ban = user.banned_global
        if(not ban or now() >= ban.expire_date):
            return (3, _('User %s is not being banned' % user.name))
        else:
            operator = ban.operator
            return (0, OK_MSG, {
                'operator': {
                    'uid': operator.id,
                    'name': operator.name,
                    'mail': operator.mail
                },
                'date': ban.date.timestamp(),
                'expire_date': ban.expire_date.timestamp(),
                'days': round(
                    (ban.expire_date - ban.date).total_seconds() / 86400
                )
            })
    except Exception as err:
        return (1, db_err_msg(err))


def ban_global_list(page, count_per_page):
    date = now()
    try:
        query = (
            BanGlobal
            .select(BanGlobal, User)
            .join(User)
            .where(date < BanGlobal.expire_date)
            .order_by(BanGlobal.date.desc())
            .paginate(page, count_per_page)
        )
    except Exception as err:
        return (1, db_err_msg(err))
    list = []
    for ban in query:
        list.append({
            'user': {
                'uid': ban.user.id,
                'name': ban.user.name,
                'mail': ban.user.mail
            },
            'operator': {
                'uid': ban.operator.id,
                'name': ban.operator.name,
                'mail': ban.operator.mail
            },
            'date': ban.date.timestamp(),
            'expire_date': ban.expire_date.timestamp(),
            'days': round(
                (ban.expire_date - ban.date).total_seconds() / 86400
            )
        })
    return (0, {'list': list, 'count': len(list)})


def ban_global_add(uid, days, operator):
    # "operator" is UID of the operator, which must be valid.
    date = now()
    delta = datetime.timedelta(days=days)
    expire_date = date + delta
    try:
        query = User.select().where(User.id == uid)
        if(not query):
            return (2, _('No such user.'))
        user = query.get()
        ban = user.banned_global
        if(ban):
            if(delta > ban.expire_date-ban.date):
                ban.date = date
                ban.operator_id = operator
                ban.expire_date = expire_date
                ban.save()
                return (0, _('Ban on user %s entered into force.' % user.name))
            else:
                return (3, _('Ban with longer term already exists.'), {
                    'operator': {
                        'uid': ban.operator.id,
                        'name': ban.operator.name,
                        'mail': ban.operator.mail
                    },
                    'date': ban.date.timestamp(),
                    'expire_date': ban.expire_date.timestamp(),
                    'days': round(
                        (ban.expire_date - ban.date).total_seconds() / 86400
                    )
                })
        else:
            BanGlobal.create(
                user = user,
                operator_id = operator,
                date = date,
                expire_date = expire_date
            )
            return (0, _('Ban on user %s entered into force.' % user.name))
    except Exception as err:
        return (1, db_err_msg(err))


def ban_global_remove(uid):
    try:
        query = User.select().where(User.id == uid)
        if(not query):
            return (1, _('No such user.'))
        user = query.get()
        ban = user.banned_global
        if(not ban or now() >= ban.expire_date):
            return (2, _('User %s is not being banned.' % user.name))
        else:
            ban.delete_instance()
            return (0, _('Ban on user %s cancelled successfully.' % user.name))
    except Exception as err:
        return (1, db_err_msg(err))


# Not Implemented Functions


# Local and Global Ban
#
# def ban_global_check(uid)
# def ban_check(uid, board)
# def ban_global_info(uid)
# def ban_info(uid, board)
# def ban_global_list(page, count_per_page)
# def ban_list(board, page, count_per_page)
# def ban_global_add(uid, days, operator)
#   Tip: if expire_time > original_expire_time, update;
#        if expire_time < original_expire_time, do nothing
#          and return a feedback.
#   Tip: operator is also uid, not user name.
# def ban_add(uid, board, days, operator)
#   Tip: The same as above.
# def ban_global_remove(uid)
# def ban_remove(uid, board)


# Board Administrators Management
#
# def board_admin_check(uid, board)
#   Tip: return the level: 1 = assistant, 2 = moderator
# def board_admin_list(board)
# def board_admin_add(uid, board)
# def board_admin_remove(uid, board)


# Topic
#
# def topic_add(board, title, author, post_body)
#   Tip: board -> short_name, author -> uid
#   Tip: Don't forget to save the date.
#   Tip: Don't forget to update last_post_date, which intends for sorting.
# def topic_remove(tid, operator)
#   Tip: Just set deleted = True, not removing the record.
#   Tip: Don't forget to save the operator and the date.
#   Tip: Checking permission of user is unnecessary.
#        (That isn't the responsibility of this function)
# def topic_list(board, page, count_per_page)
#   Tip: Return both topics and count for paging.


# Post
#
# def post_add(tid, author, content)
#   Tip: author -> uid
#   Tip: Don't forget to save the date.
#   Tip: Don't forget to update last_post_date of its topic.
#   Tip: Don't forget to set field topic_author to emit a reply.
#   Tip: Don't extract At from the content, which is not the responsibility of
#          this function.
# def post_edit(pid, new_content)
#   Tip: Don't forget to save the edit date.
# def post_remove(pid, operator)
#   Tip: The same as topic_remove()
#   Tip: Reject the requests of removing top posts (a.k.a floor #1).
# def post_list(tid, page, count_per_page)
#   Tip: Return both posts and count for paging.


# Subpost (a.k.a Post in Post)
#
# def subpost_add(pid, author, content)
#   Tip: author -> uid
#   Tip: Don't forget to save the date.
#   Tip: Don't forget to update last_post_date of its topic.
#   Tip: Don't forget to fill fields reply{0,1,2} and reply{0,1,2}_author
#          to emit replies.
#   Tip: Don't extract At from the content, which is not the responsibility of
#          this function.
# def subpost_edit(sid, new_content)
#   Tip: Don't forget to save the edit date.
# def subpost_remove(sid, operator)
#   Tip: The same as topic_remove()
# def subpost_list(pid, page, count_per_page)
#   Tip: Return both subposts and count for paging.


# Reply
#
# def reply_get(uid, page, count_per_page)
#   Tip: Get replies that user with uid "uid" received.
#   Tip: Take a union set (query) of records from the two sources.
#   Tip: Return both posts and count for paging.


# At
# def at_from_post_add(pid, caller, callee)
# Tip: caller, callee -> uid
# def at_from_subpost_add(sid, caller, callee)
# Tip: The same as above.
# def at_get(uid, page, count_per_page)
#   Tip: Get At that user with uid "uid" received.
#   Tip: Take a union set (query) of records from the two sources.
#   Tip: Return both posts and count for paging.


# Image
#
# def image_add(sha256, uid)
#   Tip: This function is only for importing the record {sha256, uid} into the
#          database. Uploading is the responsibility of the higher layer.
# def image_remove(sha256)
#   Tip: Only for database record. (as above)
# def image_list(uid, page, images_per_page)
#   Tip: Return both images and count for paging.
