#!/usr/bin/env python3


from flask import Flask, Response, request, session, redirect, url_for, escape
app = Flask(__name__)

import os
import io
import re
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import forum
import captcha
from validation import *


# Enable debug mode for test
DEBUG = True
EMAIL_ADDRESS = 'no_reply@foo.bar'


class ForumPermissionCheckError(Exception):
    pass


def _(string):
    return string # reserved for l10n


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


def validation_err_response(err):
    '''Generate responses for validation errors

    @param ValidationError err
    @return Response
    '''
    return json_response((255, _('Validation error: %s') % str(err)) )


def permission_err_response(err):
    '''Generate responses for permission check errors

    @param ForumPermissionCheckError err
    @return Response
    '''
    return json_response(err.args[0])


@app.route('/')
def index():
    uid = session.get('uid')
    if(uid):
        # for debugging
        tip = '<p>[Signed in] UID = %d</p>' % uid
    else:
        tip = ''
    return (
        '<script type="text/javascript" src="static/debug.js"></script>'
        + '<h1>It just works, but very ugly.</h1>'
        + tip
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

    result_config = forum.config_get()
    if(result_config[0] != 0):
        return json_response(result_config)
    config = result_config[2]

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
    # TODO: change into a page, not API returning unfriendly JSON.
    # And don't forget to change URL sent above.
    try:
        validate_token(_('Activation Code'), code)
    except ValidationError as err:
        return validation_err_response(err)
    return json_response(forum.user_activate(uid, code))


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

    result_config = forum.config_get()
    if(result_config[0] != 0):
        return json_response(result_config)
    config = result_config[2]

    try:
        send_mail(
            subject = _('Password Reset - %s') % config['site_name'],
            addr_from = EMAIL_ADDRESS,
            addr_to = data['mail'],
            content = (
                _('Verification Code: %s (Valid in 10 minutes)')
                % data['token']
            )
        )
        del data['mail']
        del data['token']
        return json_response(result)
    except Exception as err:
        return json_response((253, _('Failed to send mail: %s') % str(err)) )


@app.route('/api/user/password-reset/reset', methods=['POST'])
def user_reset_password():
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
def login():
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
        if(long_term):
            session.permanent = True
        else:
            session.permanent = False
    return json_response(result)


@app.route('/user/logout')
def logout():
    session.pop('uid', None)
    return redirect(url_for('index'))


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
    # TODO: summary
    summary = ''
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

    result_board = forum.topic_get_board(tid)
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

    result_board = forum.topic_get_board(tid)
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
    # subpost: argument from url
    subpost = request.args.get('subpost', '')
    try:
        validate_id(_('Parent Topic/Post ID'), parent)
        validate(_('Content'), content, not_empty=True)
        if(reply != '0'):
            validate_id(_('Subpost to Reply'), reply)
    except ValidationError as err:
        return validation_err_response(err)
    uid = session.get('uid')
    if(not uid):
        return json_response((249, _('Not signed in.')) )
    return json_response(
        forum.post_add(parent, uid, content, bool(subpost), int(reply))
    )


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
        validate_id(_('Page Number'), pn)
        validate_id(_('Count per Page'), count)
    except ValidationError as err:
        return validation_err_response(err)
    return json_response(
        forum.post_list(int(parent), int(pn), int(count), bool(subpost))
    )


if __name__ == '__main__':
    app.secret_key = os.urandom(24)
    app.run(debug=DEBUG)
