#!/usr/bin/env python3


from flask import Flask, Response, request, session, redirect, url_for, \
                  render_template
from flask_babel import Babel
app = Flask(__name__)
babel = Babel(app)

import os
import io
import re
import json
import smtplib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import forum
import captcha
from validation import *


# Enable debug mode for test
DEBUG = True
EMAIL_ADDRESS = 'no_reply@foo.bar'
# Codepoints, must be greater than 3
SUMMARY_LENGTH = 60
# Fixed for positioning
COUNT_SUBPOST = 10


# Configurations for the site
config = {}


class ForumPermissionCheckError(Exception):
    pass


# reserved for l10n
def _(string):
    return string


def send_mail(subject, addr_from, addr_to, content, html_content=''):
    '''Send an HTML email

    @param str subject
    @param str addr_from
    @param str addr_to
    @param str content
    @return void
    '''
    if(html_content):
        msg = MIMEMultipart('alternative')
        msg_plaintext = MIMEText(content, 'plain')
        msg_html = MIMEText(html_content, 'html')
        msg.attach(msg_html)
        msg.attach(msg_plaintext)
    else:
        msg = MIMEText(content, 'plain')
    msg['Subject'] = subject
    msg['From'] = addr_from
    msg['To'] = addr_to
    smtp = smtplib.SMTP('localhost')
    smtp.send_message(msg)
    smtp.quit()


def check_permission(operator, board):
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
        return (check_global[2]['admin'] or check[2]['admin'])


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
def inject_config():
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
    result = forum.topic_list(name, int(pn), items_per_page)
    if(result[0] != 0):
        return err_response(result)
    elif(len(result[2]['list']) == 0 and pn != '1'):
        return err_response((248, _('No such page.')) )
    else:
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
    uid = session.get('uid')
    if(uid):
        result_admin_site = forum.admin_check(uid)
        if(result_admin_site[0] != 0):
            return err_response(result_admin_site)
        result_admin = forum.admin_check(uid, topic_info['board'])
        if(result_admin[0] != 0):
            return err_response(result_admin)
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
            is_admin = is_admin
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
            html_content = _('Activation link: ')
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

    try:
        send_activation_mail(site_name, mail, activation_url)
    except Exception as err:
        forum.user_remove(data['uid'])
        return json_response((253, _('Failed to send mail: %s') % str(err)) )

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


@app.route('/user/register')
def user_register_form():
    return render_template('form_register.html')


@app.route('/user/login')
def user_login_form():
    return render_template('form_login.html')


@app.route('/user/logout')
def user_logout():
    session.pop('uid', None)
    session.pop('name', None)
    session.pop('mail', None)
    if(request.args.get('ret')):
        return redirect(request.args['ret'])
    else:
        return redirect(url_for('index'))


@app.route('/user/info/<name>')
def user_info(name):
    # waiting for impl
    return 'Info of user %s' % name


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


@app.route('/api/ban/add/<int:uid>')
def ban_add(uid):
    board = request.args.get('board', '')
    days = request.args.get('days', '1')
    try:
        validate(_('Days'), days, in_list=['1', '3', '10', '30'])
    except ValidationError as err:
        return validation_err_response(err)
    operator = session.get('uid')
    if(not operator):
        return json_response((254, _('Permission denied.')) )
    try:
        if(check_permission(operator, board)):
            return json_response(forum.ban_add(uid, int(days), operator, board))
        else:
            return json_response((254, _('Permission denied.')) )
    except ForumPermissionCheckError as err:
        return permission_err_response(err)


@app.route('/api/ban/remove/<int:uid>')
def ban_remove(uid):
    board = request.args.get('board', '')
    operator = session.get('uid')
    if(not operator):
        return json_response((254, _('Permission denied.')) )
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
    return json_response(forum.topic_add(board, title, uid, summary, content))


@app.route('/api/topic/move/<int:tid>')
def topic_move(tid):
    target = request.args.get('target')

    try:
        validate_board(_('Target'), target)
    except ValidationError as err:
        return validation_err_response(err)

    operator = session.get('uid')
    if(not operator):
        return json_response((254, _('Permission denied.')) )

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
    deleted = request.args.get('deleted', '')
    try:
        validate(_('Board'), board, not_empty=True)
        validate_id(_('Page Number'), pn)
        validate_id(_('Count per Page'), count)
    except ValidationError as err:
        return validation_err_response(err)
    return json_response(
        forum.topic_list(board, int(pn), int(count), bool(deleted))
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


@app.route('/api/notification/<type>')
def api_notification(type):
    pn = request.args.get('pn', '1')
    count = request.args.get('count', '10')
    try:
        validate(_('Notification Type'), type, in_list=['replyme', 'atme'])
        validate_id(_('Page Number'), pn)
        validate_id(_('Count per Page'), count)
    except ValidationError as err:
        return validation_err_response(err)
    uid = session.get('uid')
    if(uid):
        if(type == 'replyme'):
            return json_response(forum.reply_get(uid, int(pn), int(count)) )
        elif(type == 'atme'):
            return json_response(forum.at_get(uid, int(pn), int(count)) )
    else:
        return json_response((249, _('Not signed in.')) )


if __name__ == '__main__':
    result_config = forum.config_get()
    if(result_config[0] != 0):
        raise Exception('unable to load configuration from database')
    config = result_config[2]
    app.secret_key = os.urandom(24)
    app.run(debug=DEBUG)
