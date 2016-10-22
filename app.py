#!/usr/bin/env python3


from flask import Flask, Response, request, session, redirect, url_for, \
                  render_template, send_file, abort
from flask_babel import Babel
app = Flask(__name__)
babel = Babel(app)

import os
import io
import re
import json
import imghdr
import hashlib
import datetime

import forum
import captcha
from utils import *
from utils import _
from validation import *


# Enable debug mode for test
DEBUG = True
EMAIL_ADDRESS = 'no_reply@foo.bar'
# Codepoints, must be greater than 3
SUMMARY_LENGTH = 60
# Fixed for positioning
COUNT_SUBPOST = 10
# String because input is string
BAN_DAYS_LIST = ['1', '3', '10', '30']
IMAGE_FORMATS = ['png', 'gif', 'jpeg']
IMAGE_MIME = {'png': 'image/png', 'jpeg': 'image/jpeg', 'gif': 'image/gif'}

UPLOAD_FOLDER = 'upload'
MAX_UPLOAD_LENGTH = 5 * 1024 * 1024

# Configurations for the site
config = {}


class ForumPermissionCheckError(Exception):
    pass


def check_permission(operator, board, level0=False):
    '''Check if `operator` is administrator of `board` ('' means global)

    @param int operator
    @param str board
    @return bool
    '''
    check_global = forum.admin_check(operator)
    if(check_global[0] != 0):
        raise ForumPermissionCheckError(check_global)
    if(not board):
        return check_global[2]['admin']
    else:
        check = forum.admin_check(operator, board)
        if(check[0] != 0):
            raise ForumPermissionCheckError(check)
        if(not check[2]['admin']):
            board_admin = False
        else:
            if(level0):
                board_admin = (check[2]['level'] == 0)
            else:
                board_admin = True
        return (check_global[2]['admin'] or board_admin)


def json_response(result):
    '''Generate JSON responses from the return values of functions of forum.py

    @param tuple result (int, str[, dict])
    @return Response
    '''
    formatted_result = {'code': result[0], 'msg': result[1]}
    if(len(result) == 3 and result[2]):
        formatted_result['data'] = result[2]
    return Response(json.dumps(formatted_result), mimetype='application/json')


def err_response(result):
    '''Generate responses for general errors (result[0] != 0)

    @param tuple result (int, str[, dict])
    @return Response
    '''
    return render_template('error.html', result=result)


def validation_err_response(err, json=True):
    '''Generate responses for validation errors

    @param ValidationError err
    @return Response
    '''
    if(json):
        return json_response((255, _('Validation error: %s') % str(err)) )
    else:
        return render_template(
            'error.html',
            result = (255, _('Validation error: %s') % str(err))
        )


def permission_err_response(err):
    '''Generate responses for permission check errors

    @param ForumPermissionCheckError err
    @return Response
    '''
    return json_response(err.args[0])


@app.context_processor
def inject_data():
    return dict(config=config)


@app.template_filter('date')
def format_date(timestamp, detailed=False):
    # behaviour of this function must be consistent with the front-end
    if(detailed):
        return datetime.datetime.fromtimestamp(int(timestamp)).isoformat(' ');
    date = datetime.datetime.fromtimestamp(timestamp)
    delta = round((datetime.datetime.now() - date).total_seconds())
    if(delta < 60):
        return _('just now')
    elif(delta < 3600):
        minutes = delta // 60
        if(minutes == 1):
            return _('a minute ago')
        else:
            return _('%d minutes ago') % minutes
    elif(delta < 86400):
        hours = delta // 3600
        if(hours == 1):
            return _('an hour ago')
        else:
            return _('%d hours ago') % hours
    # 604800 = 86400*7
    elif(delta < 604800):
        days = delta // 86400
        if(days == 1):
            return _('a day ago')
        else:
            return _('%d days ago') % days
    # 2629746 = 86400*(31+28+97/400+31+30+31+30+31+31+30+31+30+31)/12
    elif(delta < 2629746):
        weeks = delta // 604800
        if(weeks == 1):
            return _('a week ago')
        else:
            return _('%d weeks ago') % weeks
    # 31556952 = 86400*(365+97/400)
    elif(delta < 31556952):
        months = delta // 2629746
        if(months == 1):
            return _('a month ago')
        else:
            return _('%d months ago') % months
    else:
        years = delta // 31556952
        if(years == 1):
            return _('a year ago')
        else:
            return _('%d years ago') % years


@app.route('/')
def index():
    return board('')


@app.route('/board/<name>')
def board(name):
    pn = request.args.get('pn', '1')
    items_per_page = int(config['count_topic'])
    try:
        validate_id(_('Page Number'), pn)
    except ValidationError as err:
        return validation_err_response(err, json=False)

    if(int(pn) != 1 or name == ''):
        pinned_topics = []
    else:
        result_pinned = forum.topic_list(name, 1, forum.PINNED_TOPIC_MAX, pinned=True)
        if(result_pinned[0] != 0):
            return err_response(result_pinned)
        else:
            pinned_topics = result_pinned[2]['list']

    result = forum.topic_list(name, int(pn), items_per_page)
    if(result[0] != 0):
        return err_response(result)
    elif(len(result[2]['list']) == 0 and pn != '1'):
        return err_response((248, _('No such page.')) )
    else:
        result[2]['list'] = pinned_topics + result[2]['list']
        return render_template(
            'topic_list.html',
            index = (not name),
            board = name,
            data = result[2],
            pn = int(pn),
            items_per_page = items_per_page
        )


@app.route('/topic/<int:tid>')
def topic(tid):
    pn = request.args.get('pn', '1')
    count_post = int(config['count_post'])

    try:
        validate_id(_('Page Number'), pn)
    except ValidationError as err:
        return validation_err_response(err, json=False)

    result_info = forum.topic_info(tid)
    if(result_info[0] != 0):
        return err_response(result_info)
    topic_info = result_info[2]

    is_admin = False
    is_level0_admin = False
    uid = session.get('uid')
    if(uid):
        result_admin_site = forum.admin_check(uid)
        if(result_admin_site[0] != 0):
            return err_response(result_admin_site)
        result_admin = forum.admin_check(uid, topic_info['board'])
        if(result_admin[0] != 0):
            return err_response(result_admin)
        if(result_admin_site[2]['admin']):
            is_level0_admin = True
        elif(result_admin[2]['admin']):
            is_level0_admin = (result_admin[2]['level'] == 0)
        else:
            is_level0_admin = False
        is_admin = (result_admin_site[2]['admin'] or result_admin[2]['admin'])

    result = forum.post_list(tid, int(pn), count_post)
    if(result[0] != 0):
        return err_response(result)
    elif(len(result[2]['list']) == 0):
        return err_response((248, _('No such page.')) )
    else:
        data = result[2]
        for post in data['list']:
            result_subpost = forum.post_list(
                post['pid'], 1, COUNT_SUBPOST, subpost=True
            )
            if(result_subpost[0] != 0):
                return err_response(result_subpost)
            post['subposts'] = result_subpost[2]
        return render_template(
            'topic_content.html',
            tid = tid,
            topic_info = topic_info,
            data = result[2],
            pn = int(pn),
            count_post = count_post,
            count_subpost = COUNT_SUBPOST,
            is_admin = is_admin,
            is_level0_admin = is_level0_admin
        )


@app.route('/manage/topic/move/<int:tid>')
def topic_move_form(tid):
    result_info = forum.topic_info(tid)
    if(result_info[0] != 0):
        return err_response(result_info)
    result_board = forum.board_list()
    if(result_board[0] != 0):
        return err_response(result_board)
    return render_template(
        'form_move.html',
        tid = tid,
        source = result_info[2]['board'],
        board_list = result_board[2]['list']
    )


@app.route('/api/html/subpost-list')
def html_subpost_list():
    pid = request.args.get('pid', '')
    pn = request.args.get('pn', '1')

    try:
        validate_id(_('Post ID'), pid)
        if(pn != '-1'):
            validate_id(_('Page Number'), pn)
    except ValidationError as err:
        return validation_err_response(err, json=False)

    result = forum.post_list(pid, int(pn), COUNT_SUBPOST, subpost=True)
    if(result[0] != 0):
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


@app.route('/edit/<int:id>')
def edit_form(id):
    tid = request.args.get('tid')
    subpost = request.args.get('subpost')
    # bookmark: anchor string without `#`
    bookmark = request.args.get('bookmark')

    try:
        validate_id(_('Topic ID'), tid)
    except ValidationError as err:
        return validation_err_response(err, json=False)

    result = forum.post_get_content(id, bool(subpost))
    if(result[0] != 0):
        return err_response(result)
    else:
        return render_template(
            'form_edit.html',
            id = id,
            tid = tid,
            is_subpost = bool(subpost),
            bookmark = bookmark,
            current_content = result[2]['content']
        )


@app.route('/notification/<n_type>')
def notification(n_type):
    pn = request.args.get('pn', '1')
    COUNT = 15 # TODO: user settings
    try:
        validate(_('Notification Type'), n_type, in_list=['replyme', 'atme'])
        validate_id(_('Page Number'), pn)
    except ValidationError as err:
        return validation_err_response(err)
    uid = session.get('uid')
    if(uid):
        if(n_type == 'replyme'):
            result = forum.reply_get(uid, int(pn), COUNT)
        elif(n_type == 'atme'):
            result = forum.at_get(uid, int(pn), COUNT)
        if(result[0] != 0):
            return err_response(result)
        else:
            return render_template(
                'notification.html',
                n_type = n_type,
                pn = int(pn),
                count = COUNT,
                data = result[2]
            )
    else:
        return err_response((249, _('Not signed in.')) )


@app.route('/captcha/get')
def captcha_get():
    code = captcha.gen_captcha()
    session['captcha'] = code.lower()
    image = captcha.gen_image(code)
    output = io.BytesIO()
    image.save(output, format='PNG')
    image_data = output.getvalue()
    return Response(image_data, mimetype='image/png')


@app.route('/api/user/get/name/<int:uid>')
def user_get_name(uid):
    return json_response(forum.user_get_name(uid))


@app.route('/api/user/get/uid/<username>')
def user_get_uid(username):
    try:
        validate_username(_('Username'), username)
    except ValidationError as err:
        return validation_err_response(err)
    return json_response(forum.user_get_uid(username))


@app.route('/api/user/register', methods=['POST'])
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

    if(session.get('uid')):
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

    if(captcha_text.lower() != session.get('captcha')):
        return json_response((250, _('Wrong captcha.')) )
    session.pop('captcha', None)

    result = forum.user_register(mail, name, password)
    if(result[0] != 0):
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


@app.route('/user/activate/<int:uid>/<code>')
def user_activate(uid, code):
    try:
        validate_token(_('Activation Code'), code)
    except ValidationError as err:
        return validation_err_response(err, json=False)
    result = forum.user_activate(uid, code)
    if(result[0] != 0):
        return err_response(result)
    else:
        return render_template('activated.html')


@app.route('/api/user/password-reset/get-token/<username>')
def user_password_reset_get_token(username):
    try:
        validate_username(_('Username'), username)
    except ValidationError as err:
        return validation_err_response(err)

    result_getuid = forum.user_get_uid(username)
    if(result_getuid[0] != 0):
        return json_response(result_getuid)
    uid = result_getuid[2]['uid']

    result = forum.user_password_reset_get_token(uid)
    if(result[0] != 0):
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


@app.route('/api/user/password-reset/reset', methods=['POST'])
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
    if(result_getuid[0] != 0):
        return json_response(result_getuid)
    uid = result_getuid[2]['uid']

    return json_response(forum.user_password_reset(uid, token, password))


@app.route('/api/user/login', methods=['POST'])
def user_login():
    if(session.get('uid')):
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
    if(result[0] == 0):
        session['uid'] = result[2]['uid']
        session['name'] = result[2]['name']
        session['mail'] = result[2]['mail']
        if(long_term):
            session.permanent = True
        else:
            session.permanent = False
    return json_response(result)


@app.route('/api/user/info/unread')
def user_get_unread_count():
    uid = session.get('uid')
    if(not uid):
        return json_response((249, _('Not signed in.')) )
    else:
        return json_response(forum.user_get_unread_count(uid))


@app.route('/user/register')
def user_register_form():
    return render_template('form_register.html')


@app.route('/user/login')
def user_login_form():
    return render_template('form_login.html')


@app.route('/user/ban/<name>')
def user_ban_form(name):
    board = request.args.get('board', '')
    sid = request.args.get('sid', '')
    if(not board and sid):
        result_board = forum.post_get_board(sid, subpost=True)
        if(result_board[0] != 0):
            return err_response(result_board)
        board = result_board[2]['board']
    if(board):
        globally = False
    else:
        globally = True
    result_uid = forum.user_get_uid(name)
    if(result_uid[0] != 0):
        return err_response(result_uid)
    else:
        return render_template(
            'form_ban.html',
            name = name,
            uid = result_uid[2]['uid'],
            globally = globally,
            board = board,
            days_list = BAN_DAYS_LIST
        )


@app.route('/user/logout')
def user_logout():
    session.pop('uid', None)
    session.pop('name', None)
    session.pop('mail', None)
    if(request.args.get('ret')):
        return redirect(request.args['ret'])
    else:
        return redirect(url_for('index'))


@app.route('/user/<name>')
def user(name):
    current_user = session.get('uid')
    if(current_user):
        check_result = forum.admin_check(current_user)
        if(check_result[0] != 0):
            return err_response(check_result)
        else:
            is_admin = check_result[2]['admin']
    else:
        is_admin = False
    result = forum.user_info(name)
    if(result[0] != 0):
        return err_response(result)
    else:
        return render_template(
            'user_info.html',
            name = name,
            data = result[2],
            is_admin = is_admin
        )


@app.route('/list/ban')
def list_ban():
    board = request.args.get('board', '')
    pn = request.args.get('pn', '1')
    items_per_page = int(config['count_list_item'])
    is_admin = False
    uid = session.get('uid')
    if(uid):
        admin_result = forum.admin_check(uid, board=board)
        if(admin_result[0] != 0):
            return err_response(admin_result)
        global_result = forum.admin_check(uid)
        if(global_result[0] != 0):
            return err_response(global_result)
        is_admin = admin_result[2]['admin'] or global_result[2]['admin']
    result = forum.ban_list(int(pn), items_per_page, board=board)
    if(result[0] != 0):
        return err_response(result)
    else:
        return render_template(
            'list_ban.html',
            data = result[2],
            board = board,
            is_admin = is_admin,
            pn = int(pn),
            items_per_page = items_per_page
        )


@app.route('/api/user/info/detail/<name>')
def user_info(name):
    return json_response(forum.user_info(name))


@app.route('/user/password-reset')
def user_password_reset_form():
    return render_template('form_password_reset.html')


@app.route('/api/admin/check/<int:uid>')
def admin_check(uid):
    board = request.args.get('board', '')
    try:
        if(board):
            validate_board(_('Board Name'), board)
    except ValidationError as err:
        return validation_err_response(err)
    return json_response(forum.admin_check(uid, board))


@app.route('/api/admin/add/<int:uid>')
def admin_add(uid):
    board = request.args.get('board', '')
    level = request.args.get('level', '1')
    try:
        validate_board(_('Board Name'), board)
        validate_uint(_('Administrator Level'), level)
    except ValidationError as err:
        return validation_err_response(err)

    operator = session.get('uid')
    if(not operator):
        return json_response((254, _('Permission denied.')) )

    if(level == '0'):
        check = forum.admin_check(operator)
        if(check[0] != 0):
            return json_response(check)
        if(check[2]['admin']):
            return json_response(forum.admin_add(uid, board, int(level)) )
        else:
            return json_response((254, _('Permission denied.')) )
    else:
        check_site = forum.admin_check(operator)
        check_board = forum.admin_check(operator, board)
        if(check_site[0] != 0):
            return json_response(check_site)
        if(check_board[0] != 0):
            return json_response(check_board)
        if(check_site[2]['admin']
           or (check_board[2]['admin'] and check_board[2]['level'] == 0)):
            return json_response(forum.admin_add(uid, board, int(level)) )
        else:
            return json_response((254, _('Permission denied.')) )


@app.route('/api/admin/remove/<int:uid>')
def admin_remove(uid):
    board = request.args.get('board', '')
    try:
        validate_board(_('Board Name'), board)
    except ValidationError as err:
        return validation_err_response(err)

    operator = session.get('uid')
    if(not operator):
        return json_response((254, _('Permission denied.')) )

    check = forum.admin_check(uid, board)
    if(check[0] != 0):
        return json_response(check)
    if(not check[2]['admin']):
        return json_response((4, _('No such board administrator.')) )
    if(check[2]['level'] == 0):
        check_op = forum.admin_check(operator)
        if(check_op[0] != 0):
            return json_response(check_op)
        if(check_op[2]['admin']):
            return json_response(forum.admin_remove(uid, board))
        else:
            return json_response((254, _('Permission denied.')) )
    else:
        check_site = forum.admin_check(operator)
        check_board = forum.admin_check(operator, board)
        if(check_site[0] != 0):
            return json_response(check_site)
        if(check_board[0] != 0):
            return json_response(check_board)
        if(check_site[2]['admin']
           or (check_board[2]['admin'] and check_board[2]['level'] == 0)):
            return json_response(forum.admin_remove(uid, board))
        else:
            return json_response((254, _('Permission denied.')) )


@app.route('/api/admin/list')
def admin_list():
    board = request.args.get('board', '')
    try:
        if(board):
            validate_board(_('Board Name'), board)
    except ValidationError as err:
        return validation_err_response(err)
    return json_response(forum.admin_list(board))


@app.route('/api/board/add', methods=['POST'])
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
        if(update):
            validate_board(_('Original URL Name'), original_board)
    except ValidationError as err:
        return validation_err_response(err)
    operator = session.get('uid')
    if(not operator):
        return json_response((254, _('Permission denied.')) )
    check = forum.admin_check(operator)
    if(check[0] != 0):
        return json_response(check)
    if(check[2]['admin']):
        if(not update):
            return json_response(forum.board_add(board, name, desc, announce))
        else:
            return json_response(forum.board_update(
                original_board, board, name, desc, announce
            ))
    else:
        return json_response((254, _('Permission denied.')) )


@app.route('/api/board/list')
def board_list():
    return json_response(forum.board_list())


@app.route('/api/ban/check/<int:uid>')
def ban_check(uid):
    board = request.args.get('board', '')
    try:
        if(board):
            validate_board(_('Board Name'), board)
    except ValidationError as err:
        return validation_err_response(err)
    return json_response(forum.ban_check(uid, board))


@app.route('/api/ban/info/<int:uid>')
def ban_info(uid):
    board = request.args.get('board', '')
    try:
        if(board):
            validate_board(_('Board Name'), board)
    except ValidationError as err:
        return validation_err_response(err)
    return json_response(forum.ban_info(uid, board))


@app.route('/api/ban/add/<int:uid>', methods=['POST'])
def ban_add(uid):
    board = request.form.get('board', '')
    days = request.form.get('days', '1')
    try:
        validate(_('Days'), days, in_list=BAN_DAYS_LIST)
    except ValidationError as err:
        return validation_err_response(err)
    operator = session.get('uid')
    if(not operator):
        return json_response((249, _('Not signed in.')) )
    try:
        if(check_permission(operator, board)):
            return json_response(forum.ban_add(uid, int(days), operator, board))
        else:
            return json_response((254, _('Permission denied.')) )
    except ForumPermissionCheckError as err:
        return permission_err_response(err)


@app.route('/api/ban/remove/<int:uid>', methods=['POST'])
def ban_remove(uid):
    board = request.form.get('board', '')
    operator = session.get('uid')
    if(not operator):
        return json_response((249, _('Not signed in.')) )
    try:
        if(check_permission(operator, board)):
            return json_response(forum.ban_remove(uid, board))
        else:
            return json_response((254, _('Permission denied.')) )
    except ForumPermissionCheckError as err:
        return permission_err_response(err)


@app.route('/api/ban/list')
def ban_list():
    board = request.args.get('board', '')
    pn = request.args.get('pn', '1')
    count = request.args.get('count', '10')
    try:
        if(board):
            validate_board(_('Board Name'), board)
        validate_id(_('Page Number'), pn)
        validate_id(_('Count per Page'), count)
    except ValidationError as err:
        return validation_err_response(err)
    return json_response(forum.ban_list(int(pn), int(count), board))


@app.route('/api/distillate/category/list')
def distillate_category_list():
    board = request.args.get('board', '')
    try:
        validate_board(_('Board Name'), board)
    except ValidationError as err:
        return validation_err_response(err)
    return json_response(forum.distillate_category_list(board))


@app.route('/api/distillate/category/add', methods=['POST'])
def distillate_category_add():
    board = request.form.get('board', '')
    name = request.form.get('name', '')
    try:
        validate_board(_('Board Name'), board)
        validate(_('Category Name'), name, not_empty=True)
    except ValidationError as err:
        return validation_err_response(err)
    operator = session.get('uid')
    if(not operator):
        return json_response((249, _('Not signed in.')) )
    try:
        if(check_permission(operator, board, level0=True)):
            return json_response(forum.distillate_category_add(board, name))
        else:
            return json_response((254, _('Permission denied.')) )
    except ForumPermissionCheckError as err:
        return permission_err_response(err)


@app.route('/api/distillate/category/remove', methods=['POST'])
def distillate_category_remove():
    board = request.form.get('board', '')
    name = request.form.get('name', '')
    try:
        validate_board(_('Board Name'), board)
        validate(_('Category Name'), name, not_empty=True)
    except ValidationError as err:
        return validation_err_response(err)
    operator = session.get('uid')
    if(not operator):
        return json_response((249, _('Not signed in.')) )
    try:
        if(check_permission(operator, board, level0=True)):
            return json_response(forum.distillate_category_remove(board, name))
        else:
            return json_response((254, _('Permission denied.')) )
    except ForumPermissionCheckError as err:
        return permission_err_response(err)


@app.route('/api/distillate/category/rename', methods=['POST'])
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
    if(not operator):
        return json_response((249, _('Not signed in.')) )
    try:
        if(check_permission(operator, board, level0=True)):
            return json_response(
                forum.distillate_category_rename(board, name, new_name)
            )
        else:
            return json_response((254, _('Permission denied.')) )
    except ForumPermissionCheckError as err:
        return permission_err_response(err)


@app.route('/api/topic/add', methods=['POST'])
def topic_add():
    board = request.form.get('board', '')
    title = request.form.get('title', '')
    content = request.form.get('content', '')
    if(not content):
        content = title
    s_len = SUMMARY_LENGTH
    summary = (content[:s_len-3] + '...') if len(content) > s_len else content
    try:
        validate_board(_('Board Name'), board)
        validate(_('Title'), title, max=64, not_empty=True)
    except ValidationError as err:
        return validation_err_response(err)
    uid = session.get('uid')
    if(not uid):
        return json_response((249, _('Not signed in.')) )

    result_ban_global = forum.ban_check(uid)
    if(result_ban_global[0] != 0):
        return json_response(result_ban_global)
    result_ban_local = forum.ban_check(uid, board)
    if(result_ban_local[0] != 0):
        return json_response(result_ban_local)

    if(result_ban_global[2]['banned'] or result_ban_local[2]['banned']):
        return json_response((252, _('You are being banned.')) )

    return json_response(forum.topic_add(board, title, uid, summary, content))


@app.route('/api/topic/move/<int:tid>', methods=['POST'])
def topic_move(tid):
    target = request.form.get('target')

    try:
        validate_board(_('Target'), target)
    except ValidationError as err:
        return validation_err_response(err)

    operator = session.get('uid')
    if(not operator):
        return json_response((249, _('Not signed in.')) )

    result_board = forum.topic_info(tid)
    if(result_board[0] != 0):
        return json_response(result_board)
    board = result_board[2]['board']

    try:
        if(check_permission(operator, board)):
            return json_response(forum.topic_move(tid, target))
        else:
            return json_response((254, _('Permission denied.')) )
    except ForumPermissionCheckError as err:
        return permission_err_response(err)


@app.route('/api/topic/pin/<int:tid>')
def topic_pin(tid):
    revert = request.args.get('revert', '')
    operator = session.get('uid')
    if(not operator):
        return json_response((249, _('Not signed in.')) )

    result_board = forum.topic_info(tid)
    if(result_board[0] != 0):
        return json_response(result_board)
    board = result_board[2]['board']

    try:
        if(check_permission(operator, board, level0=True)):
            return json_response(forum.topic_pin(tid, revert=bool(revert)) )
        else:
            return json_response((254, _('Permission denied.')) )
    except ForumPermissionCheckError as err:
        return permission_err_response(err)


@app.route('/api/topic/distillate/set/<int:tid>')
def topic_distillate_set(tid):
    category = request.args.get('category', '')
    try:
        validate(_('Category Name'), category, not_empty=True)
    except ValidationError as err:
        return validation_err_response(err)
    operator = session.get('uid')
    if(not operator):
        return json_response((249, _('Not signed in.')) )

    result_board = forum.topic_info(tid)
    if(result_board[0] != 0):
        return json_response(result_board)
    board = result_board[2]['board']

    try:
        if(check_permission(operator, board, level0=True)):
            return json_response(forum.topic_distillate_set(tid, category) )
        else:
            return json_response((254, _('Permission denied.')) )
    except ForumPermissionCheckError as err:
        return permission_err_response(err)


@app.route('/api/topic/distillate/unset/<int:tid>')
def topic_distillate_unset(tid):
    operator = session.get('uid')
    if(not operator):
        return json_response((249, _('Not signed in.')) )

    result_board = forum.topic_info(tid)
    if(result_board[0] != 0):
        return json_response(result_board)
    board = result_board[2]['board']

    try:
        if(check_permission(operator, board, level0=True)):
            return json_response(forum.topic_distillate_unset(tid) )
        else:
            return json_response((254, _('Permission denied.')) )
    except ForumPermissionCheckError as err:
        return permission_err_response(err)


@app.route('/api/topic/remove/<int:tid>')
def topic_remove(tid):
    revert = request.args.get('revert')

    operator = session.get('uid')
    if(not operator):
        return json_response((254, _('Permission denied.')) )

    result_board = forum.topic_info(tid)
    if(result_board[0] != 0):
        return json_response(result_board)
    board = result_board[2]['board']

    try:
        if(check_permission(operator, board)):
            if(not revert):
                return json_response(forum.topic_remove(tid, operator))
            else:
                return json_response(forum.topic_revert(tid))
        else:
            return json_response((254, _('Permission denied.')) )
    except ForumPermissionCheckError as err:
        return permission_err_response(err)


@app.route('/api/topic/list')
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


@app.route('/api/post/add', methods=['POST'])
def post_add():
    parent = request.form.get('parent', '')
    content = request.form.get('content', '')
    reply = request.form.get('reply', '0')
    # subpost: argument from URL
    subpost = request.args.get('subpost', '')
    try:
        validate_id(_('Parent Topic/Post ID'), parent)
        if(not subpost):
            validate(_('Content'), content, not_empty=True)
        else:
            validate(_('Content'), content, min=1, max=200)
        if(reply != '0'):
            validate_id(_('Subpost to Reply'), reply)
    except ValidationError as err:
        return validation_err_response(err)
    uid = session.get('uid')
    if(not uid):
        return json_response((249, _('Not signed in.')) )

    if(subpost):
        result_board = forum.post_get_board(parent)
    else:
        result_board = forum.topic_info(parent)
    if(result_board[0] != 0):
        return json_response(result_board)
    board = result_board[2]['board']
    result_ban_global = forum.ban_check(uid)
    if(result_ban_global[0] != 0):
        return json_response(result_ban_global)
    result_ban_local = forum.ban_check(uid, board)
    if(result_ban_local[0] != 0):
        return json_response(result_ban_local)

    if(result_ban_global[2]['banned'] or result_ban_local[2]['banned']):
        return json_response((252, _('You are being banned.')) )

    if(subpost):
        content = content.replace('\n', ' ').replace('\r', '')
    return json_response(
        forum.post_add(parent, uid, content, bool(subpost), int(reply))
    )


@app.route('/api/post/edit/<int:id>', methods=['POST'])
def post_edit(id):
    new_content = request.form.get('new_content')
    # subpost: argument from URL
    subpost = request.args.get('subpost')
    try:
        validate(_('New Content'), new_content, not_empty=True)
    except ValidationError as err:
        return validation_err_response(err)
    get_author = forum.post_get_author(id, bool(subpost))
    if(get_author[0] != 0):
        return json_response(get_author)
    author = get_author[2]['author']
    if(subpost):
        new_content = new_content.replace('\n', ' ').replace('\r', '')
    if(author == session.get('uid')):
        return json_response(forum.post_edit(id, new_content, bool(subpost)) )
    else:
        return json_response((254, _('Permission denied.')) )


@app.route('/api/post/remove/<int:id>')
def post_remove(id):
    revert = request.args.get('revert')
    subpost = request.args.get('subpost')

    operator = session.get('uid')
    if(not operator):
        return json_response((254, _('Permission denied.')) )

    result_board = forum.post_get_board(id, subpost=bool(subpost))
    if(result_board[0] != 0):
        return json_response(result_board)
    board = result_board[2]['board']

    try:
        if(check_permission(operator, board)):
            if(not revert):
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


@app.route('/api/post/deleted-info/<int:id>')
def post_deleted_info(id):
    subpost = request.args.get('subpost')
    return json_response(forum.post_deleted_info(id, bool(subpost)) )


@app.route('/api/post/list')
def post_list():
    parent = request.args.get('parent', '')
    pn = request.args.get('pn', '1')
    count = request.args.get('count', '10')
    subpost = request.args.get('subpost', '')
    try:
        validate_id(_('Parent Topic/Post ID'), parent)
        if(pn != '-1'):
            validate_id(_('Page Number'), pn)
        validate_id(_('Count per Page'), count)
    except ValidationError as err:
        return validation_err_response(err)
    return json_response(
        forum.post_list(
            int(parent), int(pn), int(count), bool(subpost), no_html=True
        )
    )


@app.route('/api/notification/<n_type>')
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
    if(uid):
        if(n_type == 'replyme'):
            return json_response(forum.reply_get(uid, int(pn), int(count)) )
        elif(n_type == 'atme'):
            return json_response(forum.at_get(uid, int(pn), int(count)) )
    else:
        return json_response((249, _('Not signed in.')) )


@app.route('/api/image/upload', methods=['POST'])
def image_upload():
    def sha256f(f):
        hash_sha256 = hashlib.sha256()
        for chunk in iter(lambda: f.read(4096), b''):
            hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    uid = session.get('uid')
    if(not uid):
        return json_response((249, _('Not signed in.')) )
    image = request.files.get('image')
    if(not image):
        return json_response((251, _('Invalid request.')) )
    if(not image.filename):
        return json_response((251, _('Invalid request.')) )
    img_format = imghdr.what('', image.read(100))
    if(img_format not in IMAGE_FORMATS):
        return json_response((247, _('Invalid file format.')) )
    sha256 = sha256f(image)
    filename = sha256 + '.' + img_format
    image.seek(0)
    try:
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if(not os.path.exists(path)):
            image.save(path)
        return json_response(
            forum.image_add(sha256, uid, img_format, image.filename)
        )
    except Exception as err:
        return json_response(
            (246, _('Error while saving image: %s') % str(err))
        )


@app.route('/image/<sha256>')
def image(sha256):
    try:
        validate_sha256(_('Sha256'), sha256)
    except ValidationError as err:
        abort(404)
    result = forum.image_info(sha256)
    if(result[0] != 0):
        if(result[0] == 1):
            abort(404)
        else:
            abort(500)
    else:
        img_type = result[2]['img_type']
        mime = IMAGE_MIME[img_type]
        file_name = sha256 + '.' + img_type
        path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
        return send_file(path, mime)


@app.route('/upload/image')
def upload_image_form():
    return render_template('form_upload_image.html')


if __name__ == '__main__':
    result_config = forum.config_get()
    if(result_config[0] != 0):
        raise Exception('unable to load configuration from database')
    config = result_config[2]
    app.secret_key = os.urandom(24)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_LENGTH
    app.run(debug=DEBUG)
