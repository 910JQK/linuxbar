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
from user import privilege_required
from forms import TopicAddForm, PostAddForm
from models import (
    db, Config, User, Topic, TagRelation, Tag, Post, DeleteRecord, Message
)
from pipeline import pipeline, split_lines, process_code_block, join_lines
from config import NOTIFICATION_SIGN, SUMMARY_LENGTH, DB_WILDCARD


forum = Blueprint(
    'forum', __name__, template_folder='templates', static_folder='static'
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
                    if callee and callee.id != current_user.id:
                        callees.append(callee)
                        # use "@@" to indicate this call is valid
                        arr[index] = NOTIFICATION_SIGN + segment
                index += 1
            yield ' '.join(arr)
        else:
            yield str(line)


def create_post(topic, parent, content, add_reply_count=True):
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
            Post.path % (parent_path + '/' + DB_WILDCARD)
        ).count()
        new_post = Post.create(
            topic = topic,
            parent = parent,
            ordinal = (total + 1),
            content = content,
            date = now(),
            author_id = current_user.id
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
    topic.last_reply_date = new_post.date
    topic.save()
    if add_reply_count:
        (
            Topic
            .update(reply_count = Topic.reply_count+1)
            .where(Topic.id == topic.id)
        ).execute()
    for callee in callees:
        Message.create(
            post = new_post,
            caller_id = current_user.id,
            callee = callee,                
        )            
    return new_post


@forum.route('/topic/list/<tag_slug>', methods=['GET', 'POST'])
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
            flash(_('Please sign in before publishing a topic.'), 'err')
            return redirect(url_for('user.login', next=request.url))
        title = form.title.data
        content = form.content.data
        tags = form.tags.data
        summary = ''
        if len(content) > SUMMARY_LENGTH:
            summary = content[:SUMMARY_LENGTH-3] + '...'
        else:
            summary = content
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
        first_post = create_post(
            new_topic, None, content, add_reply_count=False
        )
        flash(_('Topic published successfully.'), 'ok')
        return redirect(request.url)
    return render_template(
        'forum/topic_list.html',
        form = form,
        is_index = is_index,
        topic_list = topic_list,
        pn = pn,
        count = count,
        total = total
    )


@forum.route('/topic/<int:tid>', methods=['GET', 'POST'])
def topic_content(tid):
    def get_subpost_count(post):
        return (
            Post
            .select()
            .where(
                Post.path % (post.path+'/'+DB_WILDCARD),
                Post.is_deleted == False
            )
        ).count()
    def gen_subpost_list(post):
        return (
            Post
            .select(Post, User)
            .join(User)
            .where(
                Post.path % (post.path+'/'+DB_WILDCARD),
                Post.is_deleted == False
            )
            .order_by(Post.sort_path)
        )
    topic = find_record(Topic, id=tid)
    pn = int(request.args.get('pn', '1'))
    count = int(Config.Get('count_post'))
    form = PostAddForm()
    if topic:
        if form.validate_on_submit():
            if not current_user.is_authenticated:
                flash(_('Please sign in before publishing a post.'), 'err')
                return redirect(url_for('user.login', next=request.url))
            create_post(topic, None, form.content.data)
            flash(_('Post published successfully.'), 'ok')
            return redirect(url_for('.topic_content', tid=tid))
        posts = (
            Post
            .select(Post, User)
            .join(User)
            .where(
                Post.topic == topic,
                Post.parent == None,
                Post.is_deleted == False
            )
            .order_by(Post.date)
        )
        total = posts.count()
        post_list = posts.paginate(pn, count)
        return render_template(
            'forum/topic_content.html',
            topic = topic,
            post_list = post_list,
            form = form,
            pn = pn,
            count = count,
            total = total,
            get_subpost_count = get_subpost_count,
            gen_subpost_list = gen_subpost_list
        )
    else:
        abort(404)


@forum.route('/post/<int:pid>', methods=['GET', 'POST'])
def post(pid):
    post = find_record(Post, id=pid)
    if post:
        form = PostAddForm()
        if form.validate_on_submit():
            if not current_user.is_authenticated:
                flash(_('Please sign in before publishing a post.'), 'err')
                return redirect(url_for('user.login', next=request.url))
            create_post(post.topic, post, form.content.data)
            flash(_('Reply published successfully.'))
            return redirect(url_for('.post', pid=pid))
        post_list = (
            Post
            .select(Post, User)
            .join(User)
            .where(
                (
                    (Post.path % (post.path+'/'+DB_WILDCARD))
                    | (Post.id == pid)
                ) & (Post.is_deleted == False)
            )
            .order_by(Post.sort_path)
        )
        return render_template(
            'forum/post_content.html',
            post = post,
            form = form,
            post_list = post_list
        )
    else:
        abort(404)


@forum.route('/post/edit/<int:pid>', methods=['GET', 'POST'])
def post_edit(pid):
    post = find_record(Post, id=pid)
    if post:
        form = PostAddForm(obj=post)
        if form.validate_on_submit():
            if not current_user.is_authenticated:
                flash(_('Please sign in before editing a post.'), 'err')
                return redirect(url_for('user.login', next=request.url))
            if current_user.id != post.author.id:
                abort(401)
            form.populate_obj(post)
            post.last_edit_date = now()
            post.save()
            flash(_('Post edited successfully.'), 'ok')
            return redirect(
                request.args.get('next') or url_for('.post', pid=pid)
            )
        return render_template('forum/post_edit.html', form=form)
    else:
        abort(404)


@forum.route('/post/remove/<int:pid>', methods=['GET', 'POST'])
@privilege_required()
def post_remove(pid):
    post = find_record(Post, id=pid)
    if post and not post.is_deleted:
        next_url = request.args.get('next') or url_for('.post', pid=pid)
        if request.form.get('confirmed'):
            post.is_deleted = True
            post.save()
            DeleteRecord.create(
                post=post, date=now(), operator_id=current_user.id
            )
            flash(_('Post deleted successfully.'), 'ok')
            return redirect(next_url)
        else:
            return render_template(
                'confirm.html',
                text = _('Are you sure to delete this post?'),
                url_no = next_url
            )
    else:
        abort(404)


@forum.route('/post/revert/<int:pid>')
@privilege_required()
def post_revert(pid):
    post = find_record(Post, id=pid)
    if post and post.is_deleted:
        post.is_deleted = False
        post.save()
        DeleteRecord.create(
            post=post, date=now(), is_revert=True, operator_id=current_user.id
        )
        flash(_('Post reverted successfully.'), 'ok')
        render_template('message.html')
    else:
        abort(404)
