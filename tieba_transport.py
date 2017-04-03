#!/usr/bin/env python3


import re
import sys
from datetime import timedelta, datetime
from utils import *
from models import *
from config import DB_WILDCARD
from post import gen_summary, create_post
from fetch import fetch_kz, info


# 迷之重復發帖。找不出原因，只能先想辦法阻止第二次調用。
# 然而並沒有什麽卵用，最後還是用了終極解決方案 try ... except ...
RECENT_KEEP = 3 # minutes
recent_posts = {}
recent_subposts = {}
CALL_INTERVAL = 10 # seconds
last_call = {}


def move(kz):
    global recent_posts
    global recent_subposts
    global last_call

    info('Start moving: %d' % kz)

    date_now = now()

    if last_call.get(kz):
        if date_now - last_call[kz] < timedelta(seconds=CALL_INTERVAL):
            info('Duplicate call, exit.')
            return
    last_call[kz] = date_now
    last_call = {
        kz: date
        for kz, date in last_call.items()
        if date_now - date < timedelta(seconds=CALL_INTERVAL)
    }
    recent_posts = {
        kz: date
        for kz, date in recent_posts.items()
        if date_now - date < timedelta(minutes=RECENT_KEEP)
    }
    recent_subposts = {
        hash_value: date
        for hash_value, date in recent_subposts.items()
        if date_now - date < timedelta(minutes=RECENT_KEEP)
    }

    db.pause()
    db.unpause()

    info('Recent posts:')
    info(repr(recent_posts))
    info('Recent subposts:')
    info(repr(recent_subposts))

    updated = False
    user = find_record(User, mail='move_post@foobar')

    info('Start Fetching')
    topic = fetch_kz(kz)
    info('Writing data into database ...')
    match = re.match('^\[([0-9]+)\]', topic['title'])
    if match:
        tid = int(match.group(1))
        local_topic = find_record(Topic, id=tid)        
        if local_topic and find_record(TiebaTopic, topic=local_topic):
            local_topic = None
    else:
        local_topic = None        
    topic_rec = find_record(TiebaTopic, kz=kz)
    if not topic_rec:
        if not local_topic:
            info('Create new topic: %d' % kz)
            date_now = now()
            new_topic = Topic.create(
                author = user,
                title = topic['title'],
                summary = gen_summary(topic['posts'][0]['text'])[0],
                post_date = date_now,
                last_reply_date = date_now,
                last_reply_author = user
            )
        else:
            info('New local topic: %d -> local %d' % (kz, local_topic.id))
            new_topic = local_topic
        tieba_topic = TiebaTopic.create(
            topic = new_topic,
            kz = kz,
            last_update_date = now()
        )
    else:
        info('Ignore existing topic: %d' % kz)
        new_topic = topic_rec.topic
        tieba_topic = topic_rec
    total_reply = 0
    for post in topic['posts']:
        match = re.match('^([0-9]+).\|', post['text'])
        if match:
            pid = int(match.group(1))
            local_post = find_record(Post, id=pid)
            if local_post and find_record(TiebaPost, post=local_post):
                local_post = None
        else:
            local_post = None
        if total_reply > 0 or post.get('pid'):
            post_rec = find_record(TiebaPost, pid=post['pid'])
        else:
            # The first floor, no pid info
            post_rec = find_record(
                TiebaPost, pid=None, hash_value=sha256(str(kz))
            )
        if not post_rec and not recent_posts.get(post.get('pid', '')):
            if not local_post:
                info('Create new post: floor %d' % post['floor'])
                post['text'] = post['text'].replace('#', '##')
                content = '%(floor)d | **%(author)s** | %(date)s' % post
                if post['floor'] == 1:
                    content += ' | 原帖 http://tieba.baidu.com/p/%d' % kz
                content += '\n' + post['text']
                new_post = create_post(
                    new_topic,
                    None,
                    content,
                    author = user
                )
            else:
                info(
                    'New local post: floor %d -> local %d'
                    % (post['floor'], local_post.id)
                )
                new_post = local_post
            if post.get('pid') is not None:
                try:
                    TiebaPost.create(
                        post = new_post,
                        pid = post['pid'],
                        hash_value = None,
                        author = post['author']
                    )
                except IntegrityError:
                    info('Duplicate post detected. Remove.')
                    new_post.delete_instance()
            else:
                try:
                    TiebaPost.create(
                        post = new_post,
                        pid = None,
                        hash_value = sha256(str(kz)),
                        author = post['author']
                    )
                except IntegrityError:
                    info('Duplicate post detected. Remove.')
                    new_post.delete_instance()
            if post.get('pid'):
                recent_posts[post['pid']] = now()
            updated = True
        else:
            info('Ignore existing post: floor %d' % post['floor'])
            new_post = post_rec.post
        total_reply += 1
        for subpost in post.get('subposts', []):
            subpost['text'] = subpost['text'].replace('#', '##')
            subpost_content = '**%(author)s** | %(date)s\n%(text)s' % subpost
            hash_value = sha256(
                subpost['text'] + subpost['author'] + str(post['pid'])
            )

            match = re.search(':?.?\[([0-9]+)\]', subpost['text'])
            if match:
                pid = int(match.group(1))
                local_subpost = find_record(Post, id=pid)
                if local_subpost and find_record(TiebaPost, post=local_subpost):
                    local_subpost = None
            else:
                local_subpost = None
            subpost_rec = find_record(TiebaPost, hash_value=hash_value)
            if not subpost_rec and not recent_subposts.get(hash_value):
                if not local_subpost:
                    info('Create new subpost')
                    match = re.match('^回复.(.*).:', subpost['text'])
                    reply_target = None
                    if match:
                        reply_to = match.group(1)
                        tieba_user = find_record(TiebaUser, name=reply_to)
                        if tieba_user:
                            query = Post.select().where(
                                (Post.path % (new_post.path+'/'+DB_WILDCARD))
                                & (Post.author == tieba_user.user)
                            )
                            if query:
                                reply_target = query.get()
                    new_subpost = create_post(
                        new_topic,
                        reply_target or new_post,
                        subpost_content,
                        author = user
                    )
                else:
                    info('New local subpost -> %d' % local_subpost.id)
                    new_subpost = local_subpost
                try:
                    TiebaPost.create(
                        post = new_subpost,
                        hash_value = hash_value,
                        author = subpost['author']
                    )
                except IntegrityError:
                    info('Duplicate subpost detected. Remove.')
                    new_subpost.delete_instance()
                recent_subposts[hash_value] = now()
                updated = True
            else:
                info('Ignore existing subpost')
            total_reply += 1
    if updated:
        new_topic.reply_count = total_reply-1
        new_topic.save()
        tieba_topic.last_update_date = now()
        tieba_topic.save()
    info('Done.')

    db.pause()
    db.unpause()


if __name__ == '__main__':
    for kz_str in sys.argv[1:]:
        move(int(kz_str))
