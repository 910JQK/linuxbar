from flask_login import current_user


from utils import *
from pipeline import (
    pipeline, split_lines, process_code_block, process_line_without_format,
    join_lines
)
from models import (
    db, User, Topic, Post, DeleteRecord, Message
)
from config import NOTIFICATION_SIGN


def filter_at_messages(lines, callees):
    called = {}
    def process_segment(segment):
        if segment.startswith(NOTIFICATION_SIGN):
            callee_name = segment[1:]
            callee = find_record(User, name=callee_name)
            if (
                    callee
                    and callee.id != current_user.id
                    and not called.get(callee.id)
            ):
                callees.append(callee)
                called[callee.id] = True
                # use "@@" to indicate this call is valid
                return NOTIFICATION_SIGN + segment
        return segment
    text = ''
    for line in lines:
        if isinstance(line, str):
            yield ''.join(
                snippet
                for snippet in process_line_without_format(
                        line, process_segment
                )
            )
        else:
            yield str(line)


def create_post(topic, parent, content, add_reply_count=True, is_sys_msg=False):
    if not is_sys_msg:
        author = find_record(User, id=current_user.id)
    else:
        author = None
    callees = []
    def process_at(lines):
        return filter_at_messages(lines, callees)
    content_processor = pipeline(
        split_lines, process_code_block, process_at, join_lines
    )
    content = content_processor(content)
    if parent:
        parent_path = parent.path
        parent_sort_path = parent.sort_path
    else:
        parent_path = ''
        parent_sort_path = ''
    with db.atomic():
        total = Post.select().where(
            Post.topic == topic,
            Post.parent == parent
        ).count()
        new_post = Post.create(
            topic = topic,
            parent = parent,
            ordinal = (total + 1),
            content = content,
            date = now(),
            author = author
        )
    new_post.path = '%s/%d' % (parent_path, new_post.id)
    new_post.sort_path = (
        '%s/%s-%d' % (
            parent_sort_path,
            new_post.date.isoformat(),
            random.randrange(0, 10)
        )
    )
    new_post.save()
    if topic:
        topic.last_reply_date = new_post.date
        topic.save()
        if add_reply_count:
            (
                Topic
                .update(reply_count = Topic.reply_count+1)
                .where(Topic.id == topic.id)
            ).execute()
    for callee in callees:
        # self-to-self already filtered
        # use try_to_create() to update unread count
        Message.try_to_create(
            msg_type = 'at',
            post = new_post,
            caller = author,
            callee = callee       
        )
    p = parent
    while p:
        Message.try_to_create(
            msg_type = 'reply',
            post = new_post,
            caller = author,
            callee = p.author
        )
        p = p.parent
    if topic:
        Message.try_to_create(
            msg_type = 'reply',
            post = new_post,
            caller = author,
            callee = topic.author
        )
    return new_post


def create_system_message(content, target):
    post = create_post(None, None, content, is_sys_msg=True)
    message = Message.create(
        msg_type = 'sys',
        post = post,
        caller = None,
        callee = target
    )
    (
        User.update(unread_sys = User.unread_sys+1).where(User.id == target.id)
    ).execute()
    return message
