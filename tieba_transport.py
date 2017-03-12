#!/usr/bin/env python3


import re
import sys
from utils import *
from models import *
from post import gen_summary, create_post
from fetch import fetch_kz, info


def move(kz):
    user = find_record(User, mail='move_post@foobar')
    date_now = now()

    topic = fetch_kz(kz)
    info('Writing data into database ...')
    match = re.match('^([0-9]+)| ', topic['title'])
    if match:
        tid = int(match.group(1))
        local_topic = find_record(Topic, id=tid)
    else:
        local_topic = None

    topic_rec = find_record(TiebaTopic, kz=kz)
    if not topic_rec:
        info('Create new topic: %d' % kz)
        if not local_topic:
            new_topic = Topic.create(
                author = user,
                title = topic['title'],
                summary = gen_summary(topic['posts'][0]['text'])[0],
                post_date = date_now,
                last_reply_date = date_now,
                last_reply_author = user
            )
        else:
            new_topic = local_topic
        TiebaTopic.create(topic=new_topic, kz=kz)
    else:
        info('Ignore existing topic: %d' % kz)
        new_topic = topic_rec.topic
    total_reply = 0
    for post in topic['posts']:
        if total_reply > 0 or post.get('pid'):
            post_rec = find_record(TiebaPost, pid=post['pid'])
        else:
            # The first floor, no pid info
            if not local_topic:
                post_rec = find_record(
                    TiebaPost, pid=0, hash_value=sha256(str(kz))
                )
            else:
                local_first_post = find_record(
                    Post,
                    topic = local_topic,
                    parent = None,
                    ordinal = 1
                )
                post_rec = TiebaPost.create(
                    post = local_first_post,
                    hash_value = sha256(str(kz)),
                    pid = 0
                )
        if not post_rec:
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
            if total_reply > 0:
                TiebaPost.create(post=new_post, pid=post['pid'])
            else:
                TiebaPost.create(
                    post=new_post, pid=0, hash_value=sha256(str(kz))
                )
        else:
            info('Ignore existing post: floor %d' % post['floor'])
            new_post = post_rec.post
        total_reply += 1
        for subpost in post.get('subposts', []):
            subpost['text'] = subpost['text'].replace('#', '##')
            subpost_content = '**%(author)s** | %(date)s\n%(text)s' % subpost
            hash_value = sha256(subpost_content)
            subpost_rec = find_record(TiebaPost, hash_value=hash_value)
            if not subpost_rec:
                info('Create new subpost')
                new_subpost = create_post(
                    new_topic,
                    new_post,
                    subpost_content,
                    author = user
                )
                TiebaPost.create(post=new_subpost, hash_value=hash_value)
            else:
                info('Ignore existing subpost')
            total_reply += 1
    new_topic.reply_count = total_reply-1
    new_topic.save()
    info('Done.')


if __name__ == '__main__':
    for kz_str in sys.argv[1:]:
        move(int(kz_str))
