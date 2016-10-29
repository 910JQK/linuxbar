# -*- coding: utf-8 -*-
# TODO: define RESTful API!!!

from flask import Response, render_template, redirect, url_for, abort, request,\
    current_app, make_response, session, g, send_file

from . import api
from .. import forum
from .. import captcha
from ..utils import *
from ..utils import _
from ..validation import *


@api.route('/html/subpost-list')
def html_subpost_list():
    pid = request.args.get('pid', '')
    pn = request.args.get('pn', '1')

    try:
        validate_id(_('Post ID'), pid)
        if pn != '-1':
            validate_id(_('Page Number'), pn)
    except ValidationError as err:
        return validation_err_response(err, json=False)

    result = forum.post_list(pid, int(pn), COUNT_SUBPOST, subpost=True)
    if result[0] != 0:
        return err_response(result)
    else:
        # get the exact page number when last page (pn == -1) is specified
        page_final = result[2]['page']
        return render_template(
            'subpost_list.html',
            data = result[2],
            pid = pid,
            pn = page_final,
            count_subpost = COUNT_SUBPOST
        )


@api.route('/user/get/name/<int:uid>')
def user_get_name(uid):
    return json_response(forum.user_get_name(uid))


@api.route('/user/get/uid/<username>')
def user_get_uid(username):
    try:
        validate_username(_('Username'), username)
    except ValidationError as err:
        return validation_err_response(err)
    return json_response(forum.user_get_uid(username))


@api.route('/user/register', methods=['POST'])
def user_register():
    def send_activation_mail(site_name, mail_to, activation_url):
        '''Make an activation mail and send it by `send_mail`

        @param str site_name
        @param str mail_to
        @param str activation_url
        '''
        send_mail(
            subject = _('Activation Mail - %s') % site_name,
            addr_from = EMAIL_ADDRESS,
            addr_to = mail_to,
            content = _('Activation link: ') + activation_url,
            html = _('Activation link: ')
                + ('<a target="_blank" href="%s">%s</a>'
                % (activation_url, activation_url))
        )

    if session.get('uid'):
        return json_response((251, _('Already signed in.')))

    mail = request.form.get('mail', '')
    name = request.form.get('name', '')
    # unencrypted password: TLS is necessary
    password = request.form.get('password', '')
    captcha_text = request.form.get('captcha', '')

    try:
        validate_email(_('Mail address'), mail)
        validate_username(_('Username'), name)
        validate(_('Password'), password, not_empty=True)
        validate(_('Captcha'), captcha_text, regex=captcha.CAPTCHA_REGEX)
    except ValidationError as err:
        return validation_err_response(err)

    if captcha_text.lower() != session.get('captcha'):
        return json_response((250, _('Wrong captcha.')) )
    session.pop('captcha', None)

    result = forum.user_register(mail, name, password)
    if result[0] != 0:
        return json_response(result)
    data = result[2]

    site_name = config['site_name']
    site_url = config['site_url']
    activation_url = (
        '%s/user/activate/%d/%s' % (
            site_url,
            data['uid'],
            data['activation_code']
        )
    )
    # remove info of activation code (very important !!!)
    del data['activation_code']

    send_activation_mail(site_name, mail, activation_url)
    return json_response(result)


@api.route('/user/password-reset/get-token/<username>')
def user_password_reset_get_token(username):
    try:
        validate_username(_('Username'), username)
    except ValidationError as err:
        return validation_err_response(err)

    result_getuid = forum.user_get_uid(username)
    if result_getuid[0] != 0:
        return json_response(result_getuid)
    uid = result_getuid[2]['uid']

    result = forum.user_password_reset_get_token(uid)
    if result[0] != 0:
        return json_response(result)
    data = result[2]

    try:
        send_mail(
            subject = _('Password Reset - %s') % config['site_name'],
            addr_from = EMAIL_ADDRESS,
            addr_to = data['mail'],
            content = (
                _('Verification Code: %s (Valid in 90 minutes)')
                % data['token']
            )
        )
        del data['mail']
        del data['token']
        return json_response(result)
    except Exception as err:
        return json_response((253, _('Failed to send mail: %s') % str(err)) )


@api.route('/user/password-reset/reset', methods=['POST'])
def user_password_reset():
    username = request.form.get('username' ,'')
    token = request.form.get('token', '')
    password = request.form.get('password', '')

    try:
        validate_username(_('Username'), username)
        validate_token(_('Token'), token)
        validate(_('Password'), password, not_empty=True)
    except ValidationError as err:
        return validation_err_response(err)

    result_getuid = forum.user_get_uid(username)
    if result_getuid[0] != 0:
        return json_response(result_getuid)
    uid = result_getuid[2]['uid']

    return json_response(forum.user_password_reset(uid, token, password))


@api.route('/user/login', methods=['POST'])
def user_login():
    if session.get('uid'):
        return json_response((251, _('Already signed in.')) )
    login_name = request.form.get('login_name', '')
    password = request.form.get('password', '')
    # checkbox
    long_term = request.form.get('long_term', '')
    try:
        validate(_('Login Name'), login_name, min=3, max=64)
        validate(_('Password'), password, not_empty=True)
    except ValidationError as err:
        return validation_err_response(err)
    result = forum.user_login(login_name, password)
    if result[0] == 0:
        session['uid'] = result[2]['uid']
        session['name'] = result[2]['name']
        session['mail'] = result[2]['mail']
        if long_term:
            session.permanent = True
        else:
            session.permanent = False
    return json_response(result)


@api.route('/user/info/unread')
def user_get_unread_count():
    uid = session.get('uid')
    if not uid:
        return json_response((249, _('Not signed in.')) )
    else:
        return json_response(forum.user_get_unread_count(uid))


@api.route('/user/info/detail/<name>')
def user_info(name):
    return json_response(forum.user_info(name))


@api.route('/admin/check/<int:uid>')
def admin_check(uid):
    board = request.args.get('board', '')
    try:
        if board:
            validate_board(_('Board Name'), board)
    except ValidationError as err:
        return validation_err_response(err)
    return json_response(forum.admin_check(uid, board))


@api.route('/admin/add/<int:uid>')
def admin_add(uid):
    board = request.args.get('board', '')
    level = request.args.get('level', '1')
    try:
        validate_board(_('Board Name'), board)
        validate_uint(_('Administrator Level'), level)
    except ValidationError as err:
        return validation_err_response(err)

    operator = session.get('uid')
    if not operator:
        return json_response((254, _('Permission denied.')) )

    if level == '0':
        check = forum.admin_check(operator)
        if check[0] != 0:
            return json_response(check)
        if check[2]['admin']:
            return json_response(forum.admin_add(uid, board, int(level)) )
        else:
            return json_response((254, _('Permission denied.')) )
    else:
        check_site = forum.admin_check(operator)
        check_board = forum.admin_check(operator, board)
        if check_site[0] != 0:
            return json_response(check_site)
        if check_board[0] != 0:
            return json_response(check_board)
        if (
                check_site[2]['admin']
                or (check_board[2]['admin'] and check_board[2]['level'] == 0)
            ):
            return json_response(forum.admin_add(uid, board, int(level)) )
        else:
            return json_response((254, _('Permission denied.')) )


@api.route('/admin/remove/<int:uid>')
def admin_remove(uid):
    board = request.args.get('board', '')
    try:
        validate_board(_('Board Name'), board)
    except ValidationError as err:
        return validation_err_response(err)

    operator = session.get('uid')
    if not operator:
        return json_response((254, _('Permission denied.')) )

    check = forum.admin_check(uid, board)
    if check[0] != 0:
        return json_response(check)
    if not check[2]['admin']:
        return json_response((4, _('No such board administrator.')) )
    if check[2]['level'] == 0:
        check_op = forum.admin_check(operator)
        if check_op[0] != 0:
            return json_response(check_op)
        if check_op[2]['admin']:
            return json_response(forum.admin_remove(uid, board))
        else:
            return json_response((254, _('Permission denied.')) )
    else:
        check_site = forum.admin_check(operator)
        check_board = forum.admin_check(operator, board)
        if check_site[0] != 0:
            return json_response(check_site)
        if check_board[0] != 0:
            return json_response(check_board)
        if (
                check_site[2]['admin']
                or (check_board[2]['admin'] and check_board[2]['level'] == 0)
           ):
            return json_response(forum.admin_remove(uid, board))
        else:
            return json_response((254, _('Permission denied.')) )


@api.route('/admin/list')
def admin_list():
    board = request.args.get('board', '')
    try:
        if board:
            validate_board(_('Board Name'), board)
    except ValidationError as err:
        return validation_err_response(err)
    return json_response(forum.admin_list(board))


@api.route('/board/add', methods=['POST'])
def board_add_or_update():
    board = request.form.get('board', '')
    name = request.form.get('name', '')
    desc = request.form.get('desc', '')
    announce = request.form.get('announce', '')
    update = request.args.get('update', '')
    original_board = request.args.get('original', '')
    try:
        validate_board(_('URL Name'), board)
        validate(_('Name'), name, max=64, not_empty=True)
        validate(_('Description'), desc, max=255, not_empty=True)
        validate(_('Announcement'), announce)
        if update:
            validate_board(_('Original URL Name'), original_board)
    except ValidationError as err:
        return validation_err_response(err)
    operator = session.get('uid')
    if not operator:
        return json_response((254, _('Permission denied.')) )
    check = forum.admin_check(operator)
    if check[0] != 0:
        return json_response(check)
    if check[2]['admin']:
        if not update:
            return json_response(forum.board_add(board, name, desc, announce))
        else:
            return json_response(forum.board_update(
                original_board, board, name, desc, announce
            ))
    else:
        return json_response((254, _('Permission denied.')) )


@api.route('/board/list')
def board_list():
    return json_response(forum.board_list())


@api.route('/ban/check/<int:uid>')
def ban_check(uid):
    board = request.args.get('board', '')
    try:
        if board:
            validate_board(_('Board Name'), board)
    except ValidationError as err:
        return validation_err_response(err)
    return json_response(forum.ban_check(uid, board))


@api.route('/ban/info/<int:uid>')
def ban_info(uid):
    board = request.args.get('board', '')
    try:
        if board:
            validate_board(_('Board Name'), board)
    except ValidationError as err:
        return validation_err_response(err)
    return json_response(forum.ban_info(uid, board))


@api.route('/ban/add/<int:uid>', methods=['POST'])
def ban_add(uid):
    board = request.form.get('board', '')
    days = request.form.get('days', '1')
    try:
        validate(_('Days'), days, in_list=BAN_DAYS_LIST)
    except ValidationError as err:
        return validation_err_response(err)
    operator = session.get('uid')
    if not operator:
        return json_response((249, _('Not signed in.')) )
    try:
        if check_permission(operator, board):
            return json_response(forum.ban_add(uid, int(days), operator, board))
        else:
            return json_response((254, _('Permission denied.')) )
    except ForumPermissionCheckError as err:
        return permission_err_response(err)


@api.route('/ban/remove/<int:uid>', methods=['POST'])
def ban_remove(uid):
    board = request.form.get('board', '')
    operator = session.get('uid')
    if not operator:
        return json_response((249, _('Not signed in.')) )
    try:
        if check_permission(operator, board):
            return json_response(forum.ban_remove(uid, board))
        else:
            return json_response((254, _('Permission denied.')) )
    except ForumPermissionCheckError as err:
        return permission_err_response(err)


@api.route('/ban/list')
def ban_list():
    board = request.args.get('board', '')
    pn = request.args.get('pn', '1')
    count = request.args.get('count', '10')
    try:
        if board:
            validate_board(_('Board Name'), board)
        validate_id(_('Page Number'), pn)
        validate_id(_('Count per Page'), count)
    except ValidationError as err:
        return validation_err_response(err)
    return json_response(forum.ban_list(int(pn), int(count), board))


@api.route('/distillate/category/list')
def distillate_category_list():
    board = request.args.get('board', '')
    try:
        validate_board(_('Board Name'), board)
    except ValidationError as err:
        return validation_err_response(err)
    return json_response(forum.distillate_category_list(board))


@api.route('/distillate/category/add', methods=['POST'])
def distillate_category_add():
    board = request.form.get('board', '')
    name = request.form.get('name', '')
    try:
        validate_board(_('Board Name'), board)
        validate(_('Category Name'), name, not_empty=True)
    except ValidationError as err:
        return validation_err_response(err)
    operator = session.get('uid')
    if not operator:
        return json_response((249, _('Not signed in.')) )
    try:
        if check_permission(operator, board, level0=True):
            return json_response(forum.distillate_category_add(board, name))
        else:
            return json_response((254, _('Permission denied.')) )
    except ForumPermissionCheckError as err:
        return permission_err_response(err)


@api.route('/distillate/category/remove', methods=['POST'])
def distillate_category_remove():
    board = request.form.get('board', '')
    name = request.form.get('name', '')
    try:
        validate_board(_('Board Name'), board)
        validate(_('Category Name'), name, not_empty=True)
    except ValidationError as err:
        return validation_err_response(err)
    operator = session.get('uid')
    if not operator:
        return json_response((249, _('Not signed in.')) )
    try:
        if check_permission(operator, board, level0=True):
            return json_response(forum.distillate_category_remove(board, name))
        else:
            return json_response((254, _('Permission denied.')) )
    except ForumPermissionCheckError as err:
        return permission_err_response(err)


@api.route('/distillate/category/rename', methods=['POST'])
def distillate_category_rename():
    board = request.form.get('board', '')
    name = request.form.get('name', '')
    new_name = request.form.get('new_name', '')
    try:
        validate_board(_('Board Name'), board)
        validate(_('Category Name'), name, not_empty=True)
        validate(_('New Name'), name, not_empty=True)
    except ValidationError as err:
        return validation_err_response(err)
    operator = session.get('uid')
    if not operator:
        return json_response((249, _('Not signed in.')) )
    try:
        if check_permission(operator, board, level0=True):
            return json_response(
                forum.distillate_category_rename(board, name, new_name)
            )
        else:
            return json_response((254, _('Permission denied.')) )
    except ForumPermissionCheckError as err:
        return permission_err_response(err)


@api.route('/topic/add', methods=['POST'])
def topic_add():
    board = request.form.get('board', '')
    title = request.form.get('title', '')
    content = request.form.get('content', '')
    if not content:
        content = title
    s_len = SUMMARY_LENGTH
    summary = (content[:s_len-3] + '...') if len(content) > s_len else content
    try:
        validate_board(_('Board Name'), board)
        validate(_('Title'), title, max=64, not_empty=True)
    except ValidationError as err:
        return validation_err_response(err)
    uid = session.get('uid')
    if not uid:
        return json_response((249, _('Not signed in.')) )

    result_ban_global = forum.ban_check(uid)
    if result_ban_global[0] != 0:
        return json_response(result_ban_global)
    result_ban_local = forum.ban_check(uid, board)
    if result_ban_local[0] != 0:
        return json_response(result_ban_local)

    if result_ban_global[2]['banned'] or result_ban_local[2]['banned']:
        return json_response((252, _('You are being banned.')) )

    return json_response(forum.topic_add(board, title, uid, summary, content))


@api.route('/topic/move/<int:tid>', methods=['POST'])
def topic_move(tid):
    target = request.form.get('target')

    try:
        validate_board(_('Target'), target)
    except ValidationError as err:
        return validation_err_response(err)

    operator = session.get('uid')
    if not operator:
        return json_response((249, _('Not signed in.')) )

    result_board = forum.topic_info(tid)
    if result_board[0] != 0:
        return json_response(result_board)
    board = result_board[2]['board']

    try:
        if check_permission(operator, board):
            return json_response(forum.topic_move(tid, target))
        else:
            return json_response((254, _('Permission denied.')) )
    except ForumPermissionCheckError as err:
        return permission_err_response(err)


@api.route('/topic/pin/<int:tid>')
def topic_pin(tid):
    revert = request.args.get('revert', '')
    operator = session.get('uid')
    if not operator:
        return json_response((249, _('Not signed in.')) )

    result_board = forum.topic_info(tid)
    if result_board[0] != 0:
        return json_response(result_board)
    board = result_board[2]['board']

    try:
        if check_permission(operator, board, level0=True):
            return json_response(forum.topic_pin(tid, revert=bool(revert)) )
        else:
            return json_response((254, _('Permission denied.')) )
    except ForumPermissionCheckError as err:
        return permission_err_response(err)


@api.route('/topic/distillate/set/<int:tid>')
def topic_distillate_set(tid):
    category = request.args.get('category', '')
    try:
        validate(_('Category Name'), category, not_empty=True)
    except ValidationError as err:
        return validation_err_response(err)
    operator = session.get('uid')
    if not operator:
        return json_response((249, _('Not signed in.')) )

    result_board = forum.topic_info(tid)
    if result_board[0] != 0:
        return json_response(result_board)
    board = result_board[2]['board']

    try:
        if check_permission(operator, board, level0=True):
            return json_response(forum.topic_distillate_set(tid, category) )
        else:
            return json_response((254, _('Permission denied.')) )
    except ForumPermissionCheckError as err:
        return permission_err_response(err)


@api.route('/topic/distillate/unset/<int:tid>')
def topic_distillate_unset(tid):
    operator = session.get('uid')
    if not operator:
        return json_response((249, _('Not signed in.')) )

    result_board = forum.topic_info(tid)
    if result_board[0] != 0:
        return json_response(result_board)
    board = result_board[2]['board']

    try:
        if check_permission(operator, board, level0=True):
            return json_response(forum.topic_distillate_unset(tid) )
        else:
            return json_response((254, _('Permission denied.')) )
    except ForumPermissionCheckError as err:
        return permission_err_response(err)


@api.route('/topic/remove/<int:tid>')
def topic_remove(tid):
    revert = request.args.get('revert')

    operator = session.get('uid')
    if not operator:
        return json_response((254, _('Permission denied.')) )

    result_board = forum.topic_info(tid)
    if result_board[0] != 0:
        return json_response(result_board)
    board = result_board[2]['board']

    try:
        if check_permission(operator, board):
            if not revert:
                return json_response(forum.topic_remove(tid, operator))
            else:
                return json_response(forum.topic_revert(tid))
        else:
            return json_response((254, _('Permission denied.')) )
    except ForumPermissionCheckError as err:
        return permission_err_response(err)


@api.route('/topic/list')
def topic_list():
    board = request.args.get('board', '')
    pn = request.args.get('pn', '1')
    count = request.args.get('count', '10')
    pinned = request.args.get('pinned', '')
    distillate = request.args.get('distillate', '')
    deleted = request.args.get('deleted', '')
    try:
        validate(_('Board'), board, not_empty=True)
        validate_id(_('Page Number'), pn)
        validate_id(_('Count per Page'), count)
    except ValidationError as err:
        return validation_err_response(err)
    return json_response(
        forum.topic_list(board, int(pn), int(count), bool(deleted), bool(pinned), bool(distillate))
    )


@api.route('/post/add', methods=['POST'])
def post_add():
    parent = request.form.get('parent', '')
    content = request.form.get('content', '')
    reply = request.form.get('reply', '0')
    # subpost: argument from URL
    subpost = request.args.get('subpost', '')
    try:
        validate_id(_('Parent Topic/Post ID'), parent)
        if not subpost:
            validate(_('Content'), content, not_empty=True)
        else:
            validate(_('Content'), content, min=1, max=200)
        if reply != '0':
            validate_id(_('Subpost to Reply'), reply)
    except ValidationError as err:
        return validation_err_response(err)
    uid = session.get('uid')
    if not uid:
        return json_response((249, _('Not signed in.')) )

    if subpost:
        result_board = forum.post_get_board(parent)
    else:
        result_board = forum.topic_info(parent)
    if result_board[0] != 0:
        return json_response(result_board)
    board = result_board[2]['board']
    result_ban_global = forum.ban_check(uid)
    if result_ban_global[0] != 0:
        return json_response(result_ban_global)
    result_ban_local = forum.ban_check(uid, board)
    if result_ban_local[0] != 0:
        return json_response(result_ban_local)

    if result_ban_global[2]['banned'] or result_ban_local[2]['banned']:
        return json_response((252, _('You are being banned.')) )

    if subpost:
        content = content.replace('\n', ' ').replace('\r', '')
    return json_response(
        forum.post_add(parent, uid, content, bool(subpost), int(reply))
    )


@api.route('/post/edit/<int:id>', methods=['POST'])
def post_edit(id):
    new_content = request.form.get('new_content')
    # subpost: argument from URL
    subpost = request.args.get('subpost')
    try:
        validate(_('New Content'), new_content, not_empty=True)
    except ValidationError as err:
        return validation_err_response(err)
    get_author = forum.post_get_author(id, bool(subpost))
    if get_author[0] != 0:
        return json_response(get_author)
    author = get_author[2]['author']
    if subpost:
        new_content = new_content.replace('\n', ' ').replace('\r', '')
    if author == session.get('uid'):
        return json_response(forum.post_edit(id, new_content, bool(subpost)) )
    else:
        return json_response((254, _('Permission denied.')) )


@api.route('/post/remove/<int:id>')
def post_remove(id):
    revert = request.args.get('revert')
    subpost = request.args.get('subpost')

    operator = session.get('uid')
    if not operator:
        return json_response((254, _('Permission denied.')) )

    result_board = forum.post_get_board(id, subpost=bool(subpost))
    if result_board[0] != 0:
        return json_response(result_board)
    board = result_board[2]['board']

    try:
        if check_permission(operator, board):
            if not revert:
                return json_response(
                    forum.post_remove(id, operator, subpost=bool(subpost))
                )
            else:
                return json_response(
                    forum.post_revert(id, subpost=bool(subpost))
                )
        else:
            return json_response((254, _('Permission denied.')) )
    except ForumPermissionCheckError as err:
        return permission_err_response(err)


@api.route('/post/deleted-info/<int:id>')
def post_deleted_info(id):
    subpost = request.args.get('subpost')
    return json_response(forum.post_deleted_info(id, bool(subpost)) )


@api.route('/post/list')
def post_list():
    parent = request.args.get('parent', '')
    pn = request.args.get('pn', '1')
    count = request.args.get('count', '10')
    subpost = request.args.get('subpost', '')
    try:
        validate_id(_('Parent Topic/Post ID'), parent)
        if pn != '-1':
            validate_id(_('Page Number'), pn)
        validate_id(_('Count per Page'), count)
    except ValidationError as err:
        return validation_err_response(err)
    return json_response(
        forum.post_list(
            int(parent), int(pn), int(count), bool(subpost), no_html=True
        )
    )


@api.route('/notification/<n_type>')
def api_notification(n_type):
    pn = request.args.get('pn', '1')
    count = request.args.get('count', '10')
    try:
        validate(_('Notification Type'), n_type, in_list=['replyme', 'atme'])
        validate_id(_('Page Number'), pn)
        validate_id(_('Count per Page'), count)
    except ValidationError as err:
        return validation_err_response(err)
    uid = session.get('uid')
    if uid:
        if n_type == 'replyme':
            return json_response(forum.reply_get(uid, int(pn), int(count)) )
        elif n_type == 'atme':
            return json_response(forum.at_get(uid, int(pn), int(count)) )
    else:
        return json_response((249, _('Not signed in.')) )


@api.route('/image/upload', methods=['POST'])
def image_upload():
    def sha256f(f):
        hash_sha256 = hashlib.sha256()
        for chunk in iter(lambda: f.read(4096), b''):
            hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    uid = session.get('uid')
    if not uid:
        return json_response((249, _('Not signed in.')) )
    image = request.files.get('image')
    if not image:
        return json_response((251, _('Invalid request.')) )
    if not image.filename:
        return json_response((251, _('Invalid request.')) )
    img_format = imghdr.what('', image.read(100))
    if img_format not in IMAGE_FORMATS:
        return json_response((247, _('Invalid file format.')) )
    sha256 = sha256f(image)
    filename = sha256 + '.' + img_format
    image.seek(0)
    try:
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(path):
            image.save(path)
        return json_response(
            forum.image_add(sha256, uid, img_format, image.filename)
        )
    except Exception as err:
        return json_response(
            (246, _('Error while saving image: %s') % str(err))
        )
