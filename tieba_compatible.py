from flask import Blueprint, session, request, flash, redirect, render_template, url_for, abort
from flask_login import current_user, login_required


from utils import _
from utils import *
from forms import TiebaSyncForm
from models import Config, User, TiebaUser, TiebaTopic, Post
from config import (
    TIEBA_COMP, TIEBA_SUBMIT_URL, TIEBA_M_URL, TIEBA_FLR_URL, TIEBA_SYNC_KW
)


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
    return render_template('tieba/sync_settings.html', form=form, exist=exist)


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


def gen_url(url, **kwargs):
    return url + '?' + urlencode(kwargs)


def fetch(url, bduss, data=None, **kwargs):
    url = gen_url(url, **kwargs)
    info('Request %s' % url)
    req_headers = {'cookie': 'BDUSS=%s' % bduss}
    req = urllib.request.Request(url=url, data=data, headers=req_headers)
    response = urllib.request.urlopen(req, timeout=50)
    return BeautifulSoup(response.read(), 'lxml')


def tieba_publish_topic(topic):
    if not TIEBA_COMP:
        return
    if not session.get('bduss'):
        return
    bduss = session['bduss']
    tid = topic.id
    title = topic.title
    first_post = find_record(Post, topic=topic, parent=None, ordinal=1)
    pid = first_post.id
    content = first_post.content
    topic_url = (
        Config.Get('site_url') + url_for('forum.topic_content', tid=tid)
    )
    def send_req():
        kw = TIEBA_SYNC_KW
        m_doc = fetch(TIEBA_M_URL, bduss, kw=kw)
        data = {
            'ti': '[%d] %s' % (tid, title),
            'co': '%d | %s\n%s' % (pid, topic_url, content),
            'word': kw
        }
        for item in m_doc.find_all('input', type='hidden'):
            if item['name'] != 'kw':
                data[item['name']] = item['value']
        submit_doc = fetch(
            TIEBA_SUBMIT_URL, bduss, data=urlencode(data).encode()
        )
        # debug
        info(submit_doc.prettify())
    threading.Thread(target=send_req, args=()).start()


def tieba_publish_post(post):
    if not TIEBA_COMP:
        return
    if not session.get('bduss'):
        return
    tieba_topic = find_record(TiebaTopic, topic=post.topic)
    if not tieba_topic:
        return
    kz = tieba_topic.kz
    bduss = session['bduss']
    post_url = Config.Get('site_url') + url_for('forum.post', pid=post.id)
    def send_req():
        m_doc = fetch(TIEBA_M_URL, bduss, kz=kz)
        data = {'co': '%d | %s\n%s' % (post.id, post_url, post.content)}
        for item in m_doc.find_all('input', type='hidden'):
            data[item['name']] = item['value']
        submit_doc = fetch(
            TIEBA_SUBMIT_URL, bduss, data=urlencode(data).encode()
        )
        # debug
        info(submit_doc.prettify())
    threading.Thread(target=send_req, args=()).start()


def tieba_publish_subpost(post):
    assert post.parent
    if not TIEBA_COMP:
        return
    if not session.get('bduss'):
        return
    tieba_topic = find_record(TiebaTopic, topic=post.topic)
    if not tieba_topic:
        return
    p = post
    while p.parent != None:
        p = p.parent
    l1_post = p
    tieba_post = find_record(TiebaPost, post=l1_post)
    if not tieba_post or tieba_post.pid == 0:
        return
    kz = tieba_topic.kz
    pid = tieba_post.pid
    reply_str = ''
    if l1_post.id != post.parent.id:
        reply_tieba_post = find_record(TiebaPost, post=post.parent)
        if reply_tieba_post and reply_tieba_post.author:
            reply_str = '回复 %s: ' % reply_tieba_post.author
    bduss = session['bduss']
    def send_req():
        m_doc = fetch(TIEBA_FLR_URL, bduss, kz=kz, pid=pid)
        data = {'co': '%s[%d] %s' % (reply_str, post.id, post.content)}
        for item in m_doc.find_all('input', type='hidden'):
            data[item['name']] = item['value']
        submit_doc = fetch(
            TIEBA_SUBMIT_URL, bduss, data=urlencode(data).encode()
        )
        # debug
        info(submit_doc.prettify())
    threading.Thread(target=send_req, args=()).start()
