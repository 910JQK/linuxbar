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


def admin_check(uid, board=''):
    try:
        query = User.select().where(User.id == uid)
        if(not query):
            return (2, _('No such user.'))
        user_rec = query.get()
        admin = None
        if(not board):
            admin = user_rec.site_managing
        else:
            query = Board.select().where(Board.short_name == board)
            if(not query):
                return (3, _('No such board.'))
            board_rec = query.get()
            admin = BoardAdmin.select().where(
                BoardAdmin.user == user_rec,
                BoardAdmin.board == board_rec
            )
    except Exception as err:
        return (1, db_err_msg(err))
    if(admin):
        if(not board):
            return (0, OK_MSG, {'admin': True})
        else:
            return (0, OK_MSG, {'admin': True, 'level': admin[0].level})
    else:
        return (0, OK_MSG, {'admin': False})


def admin_list(board=''):
    try:
        query = None
        if(not board):
            query = SiteAdmin.select()
        else:
            query = Board.select().where(Board.short_name == board)
            if(not query):
                return (2, _('No such board.'))
            board_rec = query.get()
            query = BoardAdmin.select().where(BoardAdmin.board == board_rec)
        list = []
        for admin in query:
            if(not board):
                list.append(admin.user.id)
            else:
                list.append({'uid': admin.user.id, 'level': admin.level})
        return (0, OK_MSG, {'list': list, 'count': len(list)})
    except Exception as err:
        return (1, db_err_msg(err))


def admin_add(uid, board='', level=1):
    try:
        query = User.select().where(User.id == uid)
        if(not query):
            return (2, _('No such user.'))
        user_rec = query.get()
        if(not board):
            if(user_rec.site_managing):
                return (4, _('User %s is already a site administrator.'
                             % user_rec.name))
            else:
                SiteAdmin.create(user=user_rec)
                return (0, _('New site administrator %s added successfully.'
                             % user_rec.name))
        else:
            query = Board.select().where(Board.short_name == board)
            if(not query):
                return (3, _('No such board.'))
            board_rec = query.get()
            query = BoardAdmin.select().where(
                BoardAdmin.user == user_rec,
                BoardAdmin.board == board_rec
            )
            if(query):
                return (4, _(
                    'User %s is already a level-%d administrator of board %s.'
                    % (user_rec.name, query[0].level, board_rec.name)) )
            else:
                BoardAdmin.create(
                    user = user_rec,
                    board = board_rec,
                    level = level
                )
                return (0, _(
                    'New level-%d administrator of board %s - %s added successfully.'
                    % (level, board_rec.name, user_rec.name)) )
    except Exception as err:
        return (1, db_err_msg(err))


def admin_remove(uid, board=''):
    try:
        query = User.select().where(User.id == uid)
        if(not query):
            return (2, _('No such user.'))
        user_rec = query.get()
        if(not board):
            admin = user_rec.site_managing
            if(not admin):
                return (4, _('No such site administrator.'))
            else:
                admin[0].delete_instance()
                return (0, _('Site administrator %s removed successfully.'
                             % user_rec.name))
        else:
            query = Board.select().where(Board.short_name == board)
            if(not query):
                return (3, _('No such board.'))
            board_rec = query.get()
            admin = BoardAdmin.select().where(
                BoardAdmin.user == user_rec,
                BoardAdmin.board == board_rec
            )
            if(not admin):
                return (4, _('No such administrator of board %s.'
                             % board_rec.name))
            else:
                admin[0].delete_instance()
                return (0, _('Administrator %s of board %s removed successfully.'
                             % (user_rec.name, board_rec.name)) )
    except Exception as err:
        return (1, db_err_msg(err))


def board_list():
    try:
        query = Board.select()
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
    except Exception as err:
        return (1, db_err_msg(err))


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
    # dangerous operation: provide interface cautiously
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


def ban_check(uid, board=''):
    try:
        query = User.select().where(User.id == uid)
        if(not query):
            return (2, _('No such user.'))
        user_rec = query.get()

        bans = None
        if(not board):
            bans = user_rec.banned_global
        else:
            query = Board.select().where(Board.short_name == board)
            if(not query):
                return (3, _('No such board.'))
            board_rec = query.get()
            bans = Ban.select().where(
                Ban.user == user_rec,
                Ban.board == board_rec
            )
    except Exception as err:
        return (1, db_err_msg(err))
    if(bans and now() < bans[0].expire_date):
        return (0, OK_MSG, {
            'banned': True,
            'expire_date': bans[0].expire_date
        })
    else:
        return (0, OK_MSG, {'banned': False})


def ban_info(uid, board=''):
    try:
        query = User.select().where(User.id == uid)
        if(not query):
            return (2, _('No such user.'))
        user_rec = query.get()

        bans = None
        board_rec = None
        if(not board):
            bans = user_rec.banned_global
        else:
            query = Board.select().where(Board.short_name == board)
            if(not query):
                return (3, _('No such board.'))
            board_rec = query.get()
            bans = Ban.select().where(
                Ban.user == user_rec,
                Ban.board == board_rec
            )
        if(not bans or now() >= bans[0].expire_date):
            if(not board):
                return (4, _('User %s is not being banned globally.'
                             % user_rec.name))
            else:
                return (4, _('User %s is not being banned on board %s.'
                             % (user_rec.name, board_rec.name)) )
        else:
            ban = bans[0]
            return (0, OK_MSG, {
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
    except Exception as err:
        return (1, db_err_msg(err))


def ban_list(page, count_per_page, board=''):
    date = now()
    try:
        bans = None
        count = 0
        if(not board):
            count = BanGlobal.select().where(
                date < BanGlobal.expire_date
            ).count()
            bans = (
                BanGlobal
                .select(BanGlobal, User)
                .join(User)
                .where(date < BanGlobal.expire_date)
                .order_by(BanGlobal.date.desc())
                .paginate(page, count_per_page)
            )
        else:
            query = Board.select().where(Board.short_name == board)
            if(not query):
                return (2, _('No such board.'))
            board_rec = query.get()
            count = Ban.select().where(
                Ban.board == board_rec,
                date < Ban.expire_date
            ).count()
            bans = (
                Ban
                .select(Ban, User)
                .join(User)
                .where(
                    Ban.board == board_rec,
                    date < Ban.expire_date
                )
                .order_by(Ban.date.desc())
                .paginate(page, count_per_page)
            )
        list = []
        for ban in bans:
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
        return (0, OK_MSG, {'list': list, 'count': count})
    except Exception as err:
        return (1, db_err_msg(err))


def ban_add(uid, days, operator, board=''):
    # Parameter "operator" is UID of the operator, which must be valid.
    date = now()
    delta = datetime.timedelta(days=days)
    expire_date = date + delta
    try:
        query = User.select().where(User.id == uid)
        if(not query):
            return (2, _('No such user.'))
        user_rec = query.get()
        bans = None
        if(not board):
            bans = user_rec.banned_global
        else:
            query = Board.select().where(Board.short_name == board)
            if(not query):
                return (3, _('No such board.'))
            board_rec = query.get()
            bans = Ban.select().where(
                Ban.user == user_rec,
                Ban.board == board_rec
            )
        if(bans):
            ban = bans[0]
            if(delta > ban.expire_date-ban.date):
                ban.date = date
                ban.operator_id = operator
                ban.expire_date = expire_date
                ban.save()
                return (0, _('Ban on user %s entered into force.'
                             % user_rec.name))
            else:
                return (4, _('Ban with same or longer term already exists.'), {
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
            if(not board):
                BanGlobal.create(
                    user = user_rec,
                    operator_id = operator,
                    date = date,
                    expire_date = expire_date
                )
            else:
                Ban.create(
                    user = user_rec,
                    operator_id = operator,
                    board = board_rec,
                    date = date,
                    expire_date = expire_date
                )
            return (0, _('Ban on user %s entered into force.' % user_rec.name))
    except Exception as err:
        return (1, db_err_msg(err))


def ban_remove(uid, board=''):
    try:
        query = User.select().where(User.id == uid)
        if(not query):
            return (1, _('No such user.'))
        user_rec = query.get()
        bans = None
        board_rec = None
        if(not board):
            bans = user_rec.banned_global
        else:
            query = Board.select().where(Board.short_name == board)
            if(not query):
                return (2, _('No such board.'))
            board_rec = query.get()
            bans = Ban.select().where(
                Ban.user == user_rec,
                Ban.board == board_rec
            )
        if(not bans or now() >= bans[0].expire_date):
            if(not board):
                return (3, _('User %s is not being banned globally.'
                             % user_rec.name))
            else:
                return (3, _('User %s is not being banned on board %s.'
                             % (user_rec.name, board_rec.name)) )
        else:
            bans[0].delete_instance()
            return (0, _('Ban on user %s cancelled successfully.'
                         % user_rec.name))
    except Exception as err:
        return (1, db_err_msg(err))


def topic_add(board, title, author, summary, post_body):
    # Parameter "author" is the UID of the author, which must be valid.
    date = now()
    if(check_empty(title)):
        return (3, _('Title cannot be empty.'))
    if(check_empty(post_body)):
        return (4, _('Post content cannot be empty.'))
    try:
        query = Board.select().where(Board.short_name == board)
        if(not query):
            return (2, _('No such board'))
        board_rec = query.get()
        topic = Topic.create(
            title = title,
            board = board_rec,
            author_id = author,
            summary = summary,
            date = date,
            last_post_date = date,
            last_post_author_id = author
        )
        Post.create(
            content = post_body,
            author = author,
            topic = topic,
            topic_author_id = author,
            date = date
        )
        return (0, _('Topic published successfully.'), {'tid': topic.id})
    except Exception as err:
        return (1, db_err_msg(err))


def topic_move(tid, board):
    try:
        query = Board.select().where(Board.short_name == board)
        if(not query):
            return (2, _('No such board.'))
        board_rec = query.get()
        query = Topic.select().where(
            Topic.id == tid,
            Topic.deleted == False
        )
        if(not query):
            return (3, _('Topic does not exist or has been deleted.'))
        topic_rec = query.get()
        if(topic_rec.board == board_rec):
            return (4, _('Invalid move.'))
        original_name = topic_rec.board.name
        topic_rec.board = board_rec
        topic_rec.save()
        return (0, _('Topic %d moved from board %s to board %s successfully.'
                     % (topic_rec.id, original_name, board_rec.name)) )
    except Exception as err:
        return (1, db_err_msg(err))


def topic_remove(tid, operator):
    # Parameter "operator" is the UID of the operator, which must be valid.
    try:
        query = Topic.select().where(Topic.id == tid)
        if(not query):
            return (2, _('No such topic.'))
        topic = query.get()
        if(topic.deleted):
            return (3, _('Topic %d has already been deleted.' % tid))
        topic.deleted = True
        topic.delete_date = now()
        topic.delete_operator_id = operator
        topic.save()
        return (0, _('Topic %d deleted successfully.' % tid))
    except Exception as err:
        return (1, db_err_msg(err))


def topic_revert(tid):
    try:
        query = Topic.select().where(Topic.id == tid)
        if(not query):
            return (2, _('No such topic.'))
        topic = query.get()
        if(not topic.deleted):
            return (3, _('Topic %d has NOT been deleted.' % tid))
        topic.deleted = False
        topic.delete_date = None
        topic.delete_operator_id = None
        topic.save()
        return (0, _('Topic %d reverted successfully.' % tid))
    except Exception as err:
        return (1, db_err_msg(err))


def topic_list(board, page, count_per_page, only_show_deleted=False):
    try:
        query = Board.select().where(Board.short_name == board)
        if(not query):
            return (2, _('No such board.'))
        board_rec = query.get()
        count = Topic.select().where(
            Topic.board == board_rec,
            Topic.deleted == only_show_deleted
        ).count()
        query = (
            Topic
            .select(Topic, User)
            .join(User)
            .where(
                Topic.board == board_rec,
                Topic.deleted == only_show_deleted
            )
            .order_by(Topic.last_post_date.desc())
            .paginate(page, count_per_page)
        )
        list = []
        for topic in query:
            item = {
                'tid': topic.id,
                'title': topic.title,
                'summary': topic.summary,
                'author': {
                    'uid': topic.author.id,
                    'name': topic.author.name,
                    'mail': topic.author.mail
                },
                'last_post_author': {
                    'uid': topic.last_post_author.id,
                    'name': topic.last_post_author.name,
                    'mail': topic.last_post_author.mail
                },
                'reply_count': topic.reply_count,
                'date': topic.date.timestamp(),
                'last_post_date': topic.last_post_date.timestamp()
            }
            if(only_show_deleted):
                item['delete_date'] = topic.delete_date.timestamp()
                item['delete_operator'] = {
                    'uid': topic.delete_operator.id,
                    'name': topic.delete_operator.name,
                    'mail': topic.delete_operator.mail
                }
            list.append(item)
        return (0, OK_MSG, {'list': list, 'count': count})
    except Exception as err:
        return (1, db_err_msg(err))


def post_add(parent, author, content, subpost=False, reply=0):
    # Parameter "author" is the UID of the author, which must be valid.
    date = now()
    topic = None
    new_post = None
    new_subpost = None
    try:
        if(not subpost):
            query = Topic.select().where(
                Topic.id == parent,
                Topic.deleted == False
            )
            if(not query):
                return (2, _('Topic does not exist or has been deleted.'))
            topic = query.get()
            new_post = Post.create(
                topic = topic,
                author_id = author,
                content = content,
                date = date,
                topic_author = topic.author
            )
        else:
            query = Post.select().where(
                Post.id == parent,
                Post.deleted == False
            )
            if(not query):
                return (2, _('Post does not exist or has been deleted.'))
            post = query.get()
            topic = post.topic
            if(topic.deleted):
                return (3, _('The topic has already been deleted'))
            reply_rec = None
            reply_rec_author = None
            if(reply):
                query = Subpost.select().where(
                    Subpost.id == reply,
                    Subpost.reply1 == post,
                    Subpost.deleted == False
                )
                if(not query):
                    return (4, _('Invalid reply.'))
                reply_rec = query.get()
                reply_rec_author = reply_rec.author
            new_subpost = Subpost.create(
                content = content,
                author_id = author,
                date = date,
                reply0 = topic,
                reply0_author = topic.author,
                reply1 = post,
                reply1_author = post.author,
                reply2 = reply_rec,
                reply2_author = reply_rec_author
            )
        topic.last_post_date = date
        topic.last_post_author_id = author
        topic.reply_count = topic.reply_count + 1
        topic.save()
    except Exception as err:
        return (1, db_err_msg(err))
    if(not subpost):
        return (0, _('Post published successfully.'), {'pid': new_post.id})
    else:
        return (0, _('Subpost published successfully.'), {'sid': new_subpost.id})


def post_edit(id, new_content, subpost=False):
    Table = None
    post_type = ''
    if(not subpost):
        Table = Post
        post_type = 'post'
    else:
        Table = Subpost
        post_type = 'subpost'
    try:
        query = Table.select().where(Table.id == id)
        if(not query):
            return (2, _('No such %s.' % post_type))
        post = query.get()
        post.content = new_content
        post.edited = True
        post.edit_date = now()
        post.save()
        return (0, _('Edit saved successfully.'))
    except Exception as err:
        return (1, db_err_msg(err))


def post_remove(id, operator, subpost=False):
    # Parameter "operator" is the UID of the operator, which must be valid.
    Table = None
    post_type = ''
    if(not subpost):
        Table = Post
        post_type = 'Post'
    else:
        Table = Subpost
        post_type = 'Subpost'
    try:
        query = Table.select().where(Table.id == id)
        if(not query):
            return (2, _('No such %s.' % post_type.lower()))
        post = query.get()
        if(post.deleted):
            return (3, _('%s %d has already been deleted.' % (post_type, id)) )
        post.deleted = True
        post.delete_date = now()
        post.delete_operator_id = operator
        post.save()
        return (0, _('%s %d deleted successfully.' % (post_type, id)) )
    except Exception as err:
        return (1, db_err_msg(err))


def post_revert(id, subpost=False):
    # Parameter "operator" is the UID of the operator, which must be valid.
    Table = None
    post_type = ''
    if(not subpost):
        Table = Post
        post_type = 'Post'
    else:
        Table = Subpost
        post_type = 'Subpost'
    try:
        query = Table.select().where(Table.id == id)
        if(not query):
            return (2, _('No such %s.' % post_type.lower()))
        post = query.get()
        if(not post.deleted):
            return (3, _('%s %d has NOT been deleted.' % (post_type, id)) )
        post.deleted = False
        post.delete_date = None
        post.delete_operator_id = None
        post.save()
        return (0, _('%s %d reverted successfully.' % (post_type, id)) )
    except Exception as err:
        return (1, db_err_msg(err))


def post_list(parent, page, count_per_page, subpost=False):
    if(not subpost):
        Parent = Topic
        Table = Post
        parent_field = Post.topic
        post_type = 'post'
        id_name = 'pid'
    else:
        Parent = Post
        Table = Subpost
        parent_field = Subpost.reply1
        post_type = 'subpost'
        id_name = 'sid'
    try:
        query = Parent.select().where(Parent.id == parent)
        if(not query):
            return (2, _('No such %s.' % post_type))
        parent_rec = query.get()
        count = Table.select().where(parent_field == parent_rec).count()
        query = (
            Table
            .select(Table, User)
            .join(User)
            .where(parent_field == parent_rec)
            .order_by(Table.id)
            .paginate(page, count_per_page)
        )
        list = []
        for post in query:
            item = None
            if(post.deleted):
                item = {
                    id_name: post.id,
                    'delete_date': post.delete_date.timestamp(),
                    'delete_operator': {
                        'uid': post.delete_operator.id,
                        'name': post.delete_operator.name,
                        'mail': post.delete_operator.mail
                    }
                }
            else:
                item = {
                    'content': post.content,
                    'author': {
                        'uid': post.author.id,
                        'name': post.author.name,
                        'mail': post.author.mail
                    },
                    'date': post.date.timestamp()
                }
                item[id_name] = post.id
                if(post.edited):
                    item['edit_date'] = post.edit_date.timestamp()
                if(subpost and post.reply2):
                    item['reply'] = post.reply2.id
            list.append(item)
        return (0, OK_MSG, {'list': list, 'count': count})
    except Exception as err:
        return (1, db_err_msg(err))


def post_deleted_info(id, subpost=False):
    if(not subpost):
        Table = Post
        post_type = 'post'
    else:
        Table = Subpost
        post_type = 'subpost'
    try:
        query = (
            Table
            .select(Table, User)
            .join(User)
            .where(
                Table.id == id,
                Table.deleted == True
            )
        )
        if(not query):
            return (2, _('No such deleted %s.' % post_type))
        post = query.get()
        info = {
            'content': post.content,
            'author': {
                'uid': post.author.id,
                'name': post.author.name,
                'mail': post.author.mail
            },
            'delete_operator': {
                'uid': post.delete_operator.id,
                'name': post.delete_operator.name,
                'mail': post.delete_operator.mail
            },
            'date': post.date.timestamp(),
            'delete_date': post.delete_date.timestamp()
        }
        if(post.edited):
            info['edit_date'] = post.edit_date.timestamp()
        return (0, OK_MSG, info)
    except Exception as err:
        return (1, db_err_msg(err))


def reply_get(uid, page, count_per_page):
    try:
        query_user = User.select().where(User.id == uid)
        if(not query_user):
            return (2, _('No such user.'))
        user = query_user.get()
        query_post = (
            Post
            .select(
                # Tip: Don't change the order of the following rows!
                # See the sorting part for details.
                Post.id,
                Post.topic,
                Post.content,
                Post.author,
                Post.date,
                Post.edit_date,
                SQL('0 AS subpost'),
                User.id,
                User.name,
                User.mail,
                Topic.title
            )
            .join(
                User
            )
            .switch(
                Post
            )
            .join(
                Topic
            )
            .where(
                Post.topic_author == user
            )
        )
        query_subpost = (
            Subpost
            .select(
                # Tip: The same as above.
                Subpost.id,
                SQL('reply0_id AS topic_id'),
                Subpost.content,
                Subpost.author,
                Subpost.date,
                Subpost.edit_date,
                SQL('1 AS subpost'),
                User.id,
                User.name,
                User.mail,
                Topic.title
            )
            .join(
                User
            )
            .switch(
                Subpost
            )
            .join(
                Topic
            )
            .where(
                (Subpost.reply0_author == user)
                | (Subpost.reply1_author == user)
                | (Subpost.reply2_author == user)
            )
        )
        count = ( query_post | query_subpost ).count()
        query = (
            (query_post | query_subpost)
            .order_by(
                # Something ugly - SQL('"date" DESC') result in error
                # Moreover, this error won't happen if Topic is NOT joined.
                # If you know how to fix it, feel free to contribute.
                SQL('5 DESC')
            )
            .paginate(page, count_per_page)
        )
        list = []
        for reply in query:
            item = {
                'content': reply.content,
                'date': reply.date.timestamp(),
                'author': {
                    'uid': reply.author.id,
                    'name': reply.author.name,
                    'mail': reply.author.mail
                }
            }
            if(reply.edit_date):
                item['edit_date'] = reply.edit_date.timestamp()
            if(not reply.subpost):
                item['pid'] = reply.id
            else:
                item['sid'] = reply.id
            item['tid'] = reply.topic.id
            item['topic_title'] = reply.topic.title
            list.append(item)
        return (0, OK_MSG, {'list': list, 'count': count})
    except Exception as err:
        return (1, db_err_msg(err))


def at_add(id, caller, callee, subpost=False):
    # The three parameters must be valid.
    try:
        if(not subpost):
            AtFromPost.create(
                post_id = id,
                caller_id = caller,
                callee_id = callee
            )
        else:
            AtFromSubpost.create(
                subpost_id = id,
                caller_id = caller,
                callee_id = callee
            )
        return (0, _('Data stored successfully'))
    except Exception as err:
        return (1, db_err_msg(err))


def at_get(uid, page, count_per_page):
    try:
        query_post = (
            AtFromPost
            .select(
                AtFromPost.post,
                AtFromPost.caller,
                Post.id,
                Post.content,
                Post.date,
                Post.edit_date,
                Post.topic,
                Topic.title,
                SQL('0 as subpost')
            )
            .join(
                Post
            )
            .join(
                Topic
            )
            .where(
                callee_id == uid
            )
        )
        query_subpost = (
            AtFromSubpost
            .select(
                SQL('subpost_id AS post_id'),
                AtFromSubpost.caller,
                Subpost.id,
                Subpost.content,
                Subpost.date,
                Subpost.edit_date,
                SQL('subpost.reply1_id AS subpost.topic_id'),
                Topic.title,
                SQL('1 AS subpost')
            )
            .join(
                Subpost
            )
            .join(
                Topic
            )
            .where(
                callee_id == uid
            )
        )
        count = (query_post | query_subpost).count()
        query = (
            (query_post | query_subpost)
            .order_by(SQL('date DESC'))
            .paginate(page, count_per_page)
        )
        list = []
        for at in query:
            item = {
                'content': at.post.content,
                'date': at.post.date.timestamp(),
                'author': {
                    'uid': at.caller.id,
                    'name': at.caller.name,
                    'mail': at.caller.mail
                }
            }
            if(at.post.edit_date):
                item['edit_date'] = at.post.edit_date.timestamp()
            if(not at.subpost):
                item['pid'] = at.post.id
            else:
                item['sid'] = at.post.id
            item['tid'] = at.post.topic
            item['topic_title'] = at.post.topic.title
            list.append(item)
        return (0, OK_MSG, {'list': list, 'count': count})
    except Exception as err:
        return (1, db_err_msg(err))


# Not Implemented Functions


# At
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
