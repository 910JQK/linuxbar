# -*- coding: utf-8 -*-
from __future__ import division
from flask import (Response, render_template, redirect, url_for, abort, request,
    current_app, make_response, session, g, send_file)

import os
import io
import json
import imghdr
import hashlib
import datetime

from . import main
from .. import db
from .. import forum
from .. import captcha
from ..utils import *
from ..utils import _
from ..validation import *


config = {}
if os.path.exists('data-dev.db'):
    result_config = forum.config_get()
    if result_config[0] != 0:
        raise Exception('unable to load configuration from database')
    config = result_config[2]


class ForumPermissionCheckError(Exception):
    pass


def check_permission(operator, board, level0=False):
    '''Check if `operator` is administrator of `board` ('' means global)
    @param int operator
    @param str board
    @return bool
    '''
    check_global = forum.admin_check(operator)
    if check_global[0] != 0:
        raise ForumPermissionCheckError(check_global)
    if not board:
        return check_global[2]['admin']
    else:
        check = forum.admin_check(operator, board)
        if check[0] != 0:
            raise ForumPermissionCheckError(check)
        if not check[2]['admin']:
            board_admin = False
        else:
            if level0:
                board_admin = (check[2]['level'] == 0)
            else:
                board_admin = True
        return (check_global[2]['admin'] or board_admin)


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
    if json:
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


@main.app_template_filter('date')
def format_date(timestamp, detailed=False):
    # behaviour of this function must be consistent with the front-end
    if detailed:
        return datetime.datetime.fromtimestamp(int(timestamp)).isoformat(' ');
    date = datetime.datetime.fromtimestamp(timestamp)
    delta = round((datetime.datetime.now() - date).total_seconds())
    if delta < 60:
        return _('just now')
    elif delta < 3600:
        minutes = delta / 60
        if minutes == 1:
            return _('a minute ago')
        else:
            return _('%d minutes ago') % minutes
    elif delta < 86400:
        hours = delta / 3600
        if hours == 1:
            return _('an hour ago')
        else:
            return _('%d hours ago') % hours
    # 604800 = 86400*7
    elif delta < 604800:
        days = delta / 86400
        if days == 1:
            return _('a day ago')
        else:
            return _('%d days ago') % days
    # 2629746 = 86400*(31+28+97/400+31+30+31+30+31+31+30+31+30+31)/12
    elif delta < 2629746:
        weeks = delta / 604800
        if weeks == 1:
            return _('a week ago')
        else:
            return _('%d weeks ago') % weeks
    # 31556952 = 86400*(365+97/400)
    elif delta < 31556952:
        months = delta / 2629746
        if months == 1:
            return _('a month ago')
        else:
            return _('%d months ago') % months
    else:
        years = delta / 31556952
        if years == 1:
            return _('a year ago')
        else:
            return _('%d years ago') % years


@main.route('/')
def index():
    return board('')


@main.route('/board/<name>')
def board(name):
    pn = request.args.get('pn', '1')
    items_per_page = int(config['count_topic'])
    try:
        validate_id(_('Page Number'), pn)
    except ValidationError as err:
        return validation_err_response(err, json=False)

    if int(pn) != 1 or name == '':
        pinned_topics = []
    else:
        result_pinned = forum.topic_list(name, 1, forum.PINNED_TOPIC_MAX, pinned=True)
        if result_pinned[0] != 0:
            return err_response(result_pinned)
        else:
            pinned_topics = result_pinned[2]['list']

    result = forum.topic_list(name, int(pn), items_per_page)
    if result[0] != 0:
        return err_response(result)
    elif not result[2]['list'] and pn != '1':
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


@main.route('/topic/<int:tid>')
def topic(tid):
    pn = request.args.get('pn', '1')
    count_post = int(config['count_post'])

    try:
        validate_id(_('Page Number'), pn)
    except ValidationError as err:
        return validation_err_response(err, json=False)

    result_info = forum.topic_info(tid)
    if result_info[0] != 0:
        return err_response(result_info)
    topic_info = result_info[2]

    is_admin = False
    is_level0_admin = False
    uid = session.get('uid')
    if uid:
        result_admin_site = forum.admin_check(uid)
        if result_admin_site[0] != 0:
            return err_response(result_admin_site)
        result_admin = forum.admin_check(uid, topic_info['board'])
        if result_admin[0] != 0:
            return err_response(result_admin)
        if result_admin_site[2]['admin']:
            is_level0_admin = True
        elif result_admin[2]['admin']:
            is_level0_admin = (result_admin[2]['level'] == 0)
        else:
            is_level0_admin = False
        is_admin = (result_admin_site[2]['admin'] or result_admin[2]['admin'])

    result = forum.post_list(tid, int(pn), count_post)
    if result[0] != 0:
        return err_response(result)
    elif not result[2]['list']:
        return err_response((248, _('No such page.')) )
    else:
        data = result[2]
        for post in data['list']:
            result_subpost = forum.post_list(
                post['pid'], 1, COUNT_SUBPOST, subpost=True
            )
            if result_subpost[0] != 0:
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


@main.route('/manage/topic/move/<int:tid>')
def topic_move_form(tid):
    result_info = forum.topic_info(tid)
    if result_info[0] != 0:
        return err_response(result_info)
    result_board = forum.board_list()
    if result_board[0] != 0:
        return err_response(result_board)
    return render_template(
        'form_move.html',
        tid = tid,
        source = result_info[2]['board'],
        board_list = result_board[2]['list']
    )


@main.route('/edit/<int:id>')
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
    if result[0] != 0:
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


@main.route('/notification/<n_type>')
def notification(n_type):
    pn = request.args.get('pn', '1')
    COUNT = 15 # TODO: user settings
    try:
        validate(_('Notification Type'), n_type, in_list=['replyme', 'atme'])
        validate_id(_('Page Number'), pn)
    except ValidationError as err:
        return validation_err_response(err)
    uid = session.get('uid')
    if uid:
        if n_type == 'replyme':
            result = forum.reply_get(uid, int(pn), COUNT)
        elif n_type == 'atme':
            result = forum.at_get(uid, int(pn), COUNT)
        if result[0] != 0:
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


@main.route('/captcha/get')
def captcha_get():
    code = captcha.gen_captcha()
    session['captcha'] = code.lower()
    image = captcha.gen_image(code)
    output = io.BytesIO()
    image.save(output, format='PNG')
    image_data = output.getvalue()
    return Response(image_data, mimetype='image/png')


@main.route('/user/activate/<int:uid>/<code>')
def user_activate(uid, code):
    try:
        validate_token(_('Activation Code'), code)
    except ValidationError as err:
        return validation_err_response(err, json=False)
    result = forum.user_activate(uid, code)
    if result[0] != 0:
        return err_response(result)
    else:
        return render_template('activated.html')


@main.route('/user/register')
def user_register_form():
    return render_template('form_register.html')


@main.route('/user/login')
def user_login_form():
    return render_template('form_login.html')


@main.route('/user/ban/<name>')
def user_ban_form(name):
    board = request.args.get('board', '')
    sid = request.args.get('sid', '')
    if not board and sid:
        result_board = forum.post_get_board(sid, subpost=True)
        if result_board[0] != 0:
            return err_response(result_board)
        board = result_board[2]['board']
    if board:
        globally = False
    else:
        globally = True
    result_uid = forum.user_get_uid(name)
    if result_uid[0] != 0:
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


@main.route('/user/logout')
def user_logout():
    session.pop('uid', None)
    session.pop('name', None)
    session.pop('mail', None)
    if request.args.get('ret'):
        return redirect(request.args['ret'])
    else:
        return redirect(url_for('main.index'))


@main.route('/user/<name>')
def user(name):
    current_user = session.get('uid')
    if current_user:
        check_result = forum.admin_check(current_user)
        if check_result[0] != 0:
            return err_response(check_result)
        else:
            is_admin = check_result[2]['admin']
    else:
        is_admin = False
    result = forum.user_info(name)
    if result[0] != 0:
        return err_response(result)
    else:
        return render_template(
            'user_info.html',
            name = name,
            data = result[2],
            is_admin = is_admin
        )


@main.route('/list/ban')
def list_ban():
    board = request.args.get('board', '')
    pn = request.args.get('pn', '1')
    items_per_page = int(config['count_list_item'])
    is_admin = False
    uid = session.get('uid')
    if uid:
        admin_result = forum.admin_check(uid, board=board)
        if admin_result[0] != 0:
            return err_response(admin_result)
        global_result = forum.admin_check(uid)
        if global_result[0] != 0:
            return err_response(global_result)
        is_admin = admin_result[2]['admin'] or global_result[2]['admin']
    result = forum.ban_list(int(pn), items_per_page, board=board)
    if result[0] != 0:
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


@main.route('/user/password-reset')
def user_password_reset_form():
    return render_template('form_password_reset.html')


@main.route('/image/<sha256>')
def image(sha256):
    try:
        validate_sha256(_('Sha256'), sha256)
    except ValidationError as err:
        abort(404)
    result = forum.image_info(sha256)
    if result[0] != 0:
        if result[0] == 1:
            abort(404)
        else:
            abort(500)
    else:
        img_type = result[2]['img_type']
        mime = IMAGE_MIME[img_type]
        file_name = sha256 + '.' + img_type
        path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
        return send_file(path, mime)


@main.route('/upload/image')
def upload_image_form():
    return render_template('form_upload_image.html')
