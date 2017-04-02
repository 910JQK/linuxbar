from flask import Blueprint, session, request, flash, redirect, render_template, url_for, abort
from flask_login import current_user, login_required


from utils import _
from utils import *
from forms import TiebaSyncForm
from post import create_system_message
from models import Config, User, TiebaUser, TiebaTopic, TiebaPost, Post
from pipeline import (
    pipeline, split_lines, process_code_block, join_lines
)
from config import (
    TIEBA_COMP, TIEBA_SUBMIT_URL, TIEBA_M_URL, TIEBA_FLR_URL, TIEBA_SYNC_KW,
    IMAGE_SIGN
)


import re
import threading
import urllib.request
from urllib.parse import urlencode
from bs4 import BeautifulSoup


tieba = Blueprint(
    'tieba', __name__, template_folder='templates', static_folder='static'
)


@tieba.route('/sync/settings', methods=['GET', 'POST'])
@login_required
def sync_settings():
    user = find_record(User, id=current_user.id)
    tieba_user = find_record(TiebaUser, user=user)
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if tieba_user:
        exist = True
        tieba_user.bduss = ''
        form = TiebaSyncForm(obj=tieba_user)
    else:
        exist = False
        form = TiebaSyncForm()
    if form.validate_on_submit():
        if not exist:
            tieba_user = TiebaUser(user=user)
        form.populate_obj(tieba_user)
        if tieba_user.set_bduss(form.bduss.data, form.password.data):
            tieba_user.save(force_insert=(not exist))
            session_save_bduss(form.password.data)
            if exist:
                flash(_('Sync settings updated successfully.'), 'ok')
            else:
                flash(_('Sync settings saved successfully.'), 'ok')
            return redirect(url_for('.sync_settings'))
        else:
            flash(_('Wrong Password!'), 'err')
    return render_template(
        'tieba/sync_settings.html',
        form = form,
        exist = exist,
        ip = ip
    )


@tieba.route('/sync/stop', methods=['GET', 'POST'])
@login_required
def sync_stop():
    if request.form.get('confirmed'):
        user = find_record(User, id=current_user.id)
        tieba_user = find_record(TiebaUser, user=user)
        if tieba_user:
            tieba_user.delete_instance()
            session_clear_bduss()
            flash(_('Sync stopped successfully.'), 'ok')
        return redirect(url_for('.sync_settings'))
    else:
        return render_template(
            'confirm.html',
            text = _('Are you sure to stop sync between Tieba ?'),
            url_no = url_for('.sync_settings')
        )


def tieba_filter(lines):
    def process_segment(segment):
        if (
            segment.startswith(IMAGE_SIGN)
            and REGEX_SHA256_PART.fullmatch(segment[len(IMAGE_SIGN):])
        ):
            hash_part = segment[len(IMAGE_SIGN):]
            image_query = (
                Image
                .select()
                .where(
                    Image.sha256.startswith(
                        hash_part
                    )
                )
            )
            if image_query:
                return process_link(
                    Config.Get('site_url')
                    + url_for('image.get', sha256part=hash_part)
                )
        return segment
    for line in lines:
        if isinstance(line, str):
            yield (
                ' '.join(process_segment(segment) for segment in line.split(' '))
            )
        else:
            yield str(line)


def tieba_content_convert(content):
    processor = pipeline(
        split_lines, process_code_block, tieba_filter, join_lines
    )
    return processor(content)


def session_save_bduss(password):
    if not TIEBA_COMP:
        return
    user = find_record(User, id=current_user.id)
    tieba_user = find_record(TiebaUser, user=user)
    if tieba_user:
        session['bduss'] = tieba_user.get_bduss(password)
    else:
        session['bduss'] = ''


def session_clear_bduss():
    if TIEBA_COMP:
        session['bduss'] = ''


def process_link(url):
    return re.sub('^https?://', '', url)


def gen_url(url, **kwargs):
    return url + '?' + urlencode(kwargs)


def get_additional_args():
    user = find_record(User, id=current_user.id)
    tieba_user = find_record(TiebaUser, user=user)
    assert tieba_user
    return {'fakeip': tieba_user.fakeip, 'ua': tieba_user.ua}


def fetch(url, bduss, data=None, fakeip='', ua='', **kwargs):
    url = gen_url(url, **kwargs)
    info('Request %s' % url)
    req_headers = {'cookie': 'BDUSS=%s' % bduss}
    if fakeip:
        req_headers['X-Forwarded-For'] = fakeip
        req_headers['Client-IP'] = fakeip
    if ua:
        req_headers['User-Agent'] = ua
    req = urllib.request.Request(url=url, data=data, headers=req_headers)
    response = urllib.request.urlopen(req, timeout=50)
    return BeautifulSoup(response.read(), 'lxml')


def send_failed_message(user, submit_doc):
    create_system_message(
        _('Failed to submit your post to tieba.')
        + '\n'
        + _('The returned document is as follows:')
        + '\n'
        + submit_doc.prettify(),
        user
    )


def tieba_publish_topic(topic):
    if not TIEBA_COMP:
        return
    if not session.get('bduss'):
        return
    user = find_record(User, id=current_user.id)
    bduss = session['bduss']
    args = get_additional_args()
    tid = topic.id
    title = topic.title
    first_post = find_record(Post, topic=topic, parent=None, ordinal=1)
    pid = first_post.id
    content = tieba_content_convert(first_post.content)
    topic_url = process_link(
        Config.Get('site_url') + url_for('forum.topic_content', tid=tid)
    )
    def send_req():
        kw = TIEBA_SYNC_KW
        m_doc = fetch(TIEBA_M_URL, bduss, kw=kw, **args)
        data = {
            'ti': '[%d] %s' % (tid, title),
            'co': '%d | %s\n%s' % (pid, topic_url, content),
            'word': kw
        }
        for item in m_doc.find_all('input', type='hidden'):
            if item['name'] != 'kw':
                data[item['name']] = item['value']
        submit_doc = fetch(
            TIEBA_SUBMIT_URL, bduss, data=urlencode(data).encode(), **args
        )
        if not submit_doc.find('span', text='发贴成功'):
            send_failed_message(user, submit_doc)
    threading.Thread(target=send_req, args=()).start()


def tieba_publish_post(post):
    if not TIEBA_COMP:
        return
    if not session.get('bduss'):
        return
    tieba_topic = find_record(TiebaTopic, topic=post.topic)
    if not tieba_topic:
        return
    user = find_record(User, id=current_user.id)
    kz = tieba_topic.kz
    bduss = session['bduss']
    args = get_additional_args()
    content = tieba_content_convert(post.content)
    post_url = process_link(
        Config.Get('site_url') + url_for('forum.post', pid=post.id)
    )
    def send_req():
        m_doc = fetch(TIEBA_M_URL, bduss, kz=kz, **args)
        data = {'co': '%d | %s\n%s' % (post.id, post_url, content)}
        for item in m_doc.find_all('input', type='hidden'):
            data[item['name']] = item['value']
        submit_doc = fetch(
            TIEBA_SUBMIT_URL, bduss, data=urlencode(data).encode(), **args
        )
        if not submit_doc.find('span', text='回贴成功'):
            send_failed_message(user, submit_doc)
    threading.Thread(target=send_req, args=()).start()


def tieba_publish_subpost(post):
    if not TIEBA_COMP:
        return
    if not session.get('bduss'):
        return
    tieba_topic = find_record(TiebaTopic, topic=post.topic)
    if not tieba_topic:
        return
    if not post.parent and post.ordinal == 1:
        return
    p = post
    while p.parent != None:
        p = p.parent
    l1_post = p
    tieba_post = find_record(TiebaPost, post=l1_post)
    if not tieba_post or tieba_post.pid == 0:
        return
    user = find_record(User, id=current_user.id)
    kz = tieba_topic.kz
    pid = tieba_post.pid
    reply_str = ''
    if l1_post.id != post.parent.id:
        reply_tieba_post = find_record(TiebaPost, post=post.parent)
        if reply_tieba_post and reply_tieba_post.author:
            reply_str = '回复 %s: ' % reply_tieba_post.author
    bduss = session['bduss']
    args = get_additional_args()
    content = tieba_convert_content(post.content)
    def send_req():
        m_doc = fetch(TIEBA_FLR_URL, bduss, kz=kz, pid=pid, **args)
        data = {'co': '%s[%d] %s' % (reply_str, post.id, content)}
        for item in m_doc.find_all('input', type='hidden'):
            data[item['name']] = item['value']
        submit_doc = fetch(
            TIEBA_SUBMIT_URL, bduss, data=urlencode(data).encode(), **args
        )
        if not submit_doc.find('span', text='回贴成功'):
            send_failed_message(user, submit_doc)
    threading.Thread(target=send_req, args=()).start()
