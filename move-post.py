#!/usr/bin/env python3


import sys
from utils import *
from models import *
from post import gen_summary, create_post
from fetch import fetch_kz, info


def move(kz):
    user = find_record(User, name='搬運')
    date_now = now()
    topic = fetch_kz(kz)
    info('Writing data into database ...')
    new_topic = Topic.create(
        author = user,
        title = topic['title'],
        summary = gen_summary(topic['posts'][0]['text'])[0],
        post_date = date_now,
        last_reply_date = date_now,
        last_reply_author = user
    )
    total_reply = 0
    for post in topic['posts']:
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
        total_reply += 1
        for subpost in post.get('subposts', []):
            subpost['text'] = subpost['text'].replace('#', '##')
            create_post(
                new_topic,
                new_post,
                '**%(author)s** | %(date)s\n%(text)s' % subpost,
                author = user
            )
            total_reply += 1
    new_topic.reply_count = total_reply-1
    new_topic.save()
    info('Done.')


if __name__ == '__main__':
    move(int(sys.argv[1]))
