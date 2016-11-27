from flask import (
    Blueprint,
    request,
    render_template,
    redirect,
    send_file,
    flash,
    abort,
    url_for
)
from flask_login import current_user, login_required


from utils import _
from utils import *
from forms import TopicAddForm
from models import Config, User, Topic, TagRelation, Tag, Post
from pipeline import pipeline, split_lines, process_code_block, join_lines
from config import NOTIFICATION_SIGN, SUMMARY_LENGTH


topic = Blueprint(
    'topic', __name__, template_folder='templates', static_folder='static'
)


def filter_at_messages(lines, callees):
    text = ''
    for line in lines:
        if isinstance(line, str):
            arr = line.split(' ')
            index = 0
            for segment in arr:
                if segment.startswith(NOTIFICATION_SIGN):
                    callee_name = segment[1:]
                    callee = find_record(User, name=callee_name)
                    if callee:
                        callees.append(callee)
                        # use "@@" to indicate this call is valid
                        arr[index] = NOTIFICATION_SIGN + segment
                index += 1
            yield ' '.join(arr)
        else:
            yield str(line)


@topic.route('/list/<tag_slug>', methods=['GET', 'POST'])
def topic_list(tag_slug):
    pn = int(request.args.get('pn', '1'))
    count = int(Config.Get('count_topic'))
    distillate_only = bool(request.args.get('distillate', ''))
    distillate_condition = (not distillate_only or Topic.distillate == True)
    if not tag_slug:
        is_index = True
    else:
        is_index = False
    if is_index:
        pinned_topics = (
            Topic
            .select(Topic, User)
            .join(User)
            .where(Topic.is_pinned==True, distillate_condition)
            .order_by(Topic.post_date)
        )
        topics = (
            Topic
            .select(Topic, User)
            .join(User)
            .where(Topic.is_pinned==False, distillate_condition)
        )
        total = topics.count()
        topics = (
            topics
            .order_by(Topic.last_reply_date.desc())
            .paginate(pn, count)
        )
        def get_topic_list():
            for I in pinned_topics:
                yield I
            for I in topics:
                yield I
        topic_list = get_topic_list()
    else:
        relation_list = (
            TagRelation
            .select(TagRelation, Tag, Topic, User)
            .join(Tag)
            .switch(TagRelation)
            .join(Topic)
            .join(User)
            .where(Tag.slug == tag_slug, distillate_condition)
        )
        total = relation_list.count()
        relation_list = (
            relation_list
            .order_by(Topic.last_reply_date.desc())
            .paginate(pn, count)
        )
        def get_topic_list():
            for relation in relation_list:
                yield relation.topic
        topic_list = get_topic_list()
    form = TopicAddForm()
    form.tags.choices = [(tag.slug, tag.name) for tag in Tag.select()]
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash(_('Please sign in before publishing a topic.'))
            return redirect(url_for('user.login', next=request.url))
        title = form.title.data
        content = form.content.data
        tags = form.tags.data
        summary = ''
        if len(content) > SUMMARY_LENGTH:
            summary = content[:SUMMARY_LENGTH-3] + '...'
        else:
            summary = content
        callees = []
        def process_at(lines):
            return filter_at_messages(lines, callees)
        content_processor = pipeline(
            split_lines, process_code_block, process_at, join_lines
        )
        content = content_processor(content)
        date_now = now()
        new_topic = Topic.create(
            author_id = current_user.id,
            title = title,
            summary = summary,
            post_date = date_now,
            last_reply_date = date_now,
            last_reply_author_id = current_user.id
        )
        for tag in tags:
            TagRelation.create(topic=new_topic, tag=find_record(Tag, slug=tag))
        first_post = Post.create(
            topic = new_topic,
            ordinal = 1,
            content = content,
            date = date_now,
            author_id = current_user.id
        )
        for callee in callees:
            Message.create(
                post = first_post,
                caller_id = current_user.id,
                callee = callee,                
            )            
        flash(_('Topic published successfully.'))
    return render_template(
        'topic/list.html',
        form = form,
        is_index = is_index,
        topic_list = topic_list,
        pn = pn,
        count = count,
        total = total
    )


@topic.route('/<int:tid>')
def content(tid):
    pass
