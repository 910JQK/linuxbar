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
from peewee import prefetch


from utils import _
from utils import *
from user import privilege_required
from post import (
    gen_summary, create_post, create_system_message
)
from forms import TopicAddForm, TopicTagManageForm, PostAddForm
from models import (
    db, Config, User, Topic, TagRelation, Tag, Post, DeleteRecord, Message
)
from config import DB_WILDCARD, PID_SIGN, TID_SIGN
from tieba_compatible import (
    tieba_publish_topic, tieba_publish_post, tieba_publish_subpost
)


forum = Blueprint(
    'forum', __name__, template_folder='templates', static_folder='static'
)


def get_topics(condition, pn, count, tag=''):
    # get topics with tags
    if tag:
        query_topic = (
            Topic
            .select(Topic, User, TagRelation, Tag)
            .join(User)
            .switch(Topic)
            .join(TagRelation)
            .join(Tag)
            .where(
                (Tag.slug == tag)
                & condition
            )
            .order_by(Topic.last_reply_date.desc())
            .paginate(pn, count)
        )
    else:
        query_topic = (
            Topic
            .select(Topic, User)
            .join(User)
            .where(condition)
            .order_by(Topic.last_reply_date.desc())
            .paginate(pn, count)
        )
    query_relation = (
        TagRelation
        .select(TagRelation, Tag)
        .join(Tag)
    )
    if tag:
        total = (
            Topic
            .select(Topic, TagRelation, Tag)
            .join(TagRelation)
            .join(Tag)
            .where(
                (Tag.slug == tag)
                & condition
            )
            .count()
        )
    else:
        total = Topic.select().where(condition).count()
    pf = prefetch(query_topic, query_relation)
    def get_list():
        for topic in pf:
            topic.tags = [relation.tag for relation in topic.tags_prefetch]
            yield topic
    return (get_list(), total)


@forum.route('/topic/list/<tag_slug>', methods=['GET', 'POST'])
def topic_list(tag_slug):
    pn = int(request.args.get('pn', '1'))
    count = int(Config.Get('count_topic'))
    distillate_only = bool(request.args.get('dist', ''))
    distillate_condition = (not distillate_only or Topic.is_distillate == True)
    if not tag_slug:
        is_index = True
        tag_record = None
    else:
        is_index = False
        tag_record = find_record(Tag, slug=tag_slug)
    if is_index:
        pinned_topics = (
            Topic
            .select(Topic, User)
            .join(User)
            .where(
                (Topic.is_pinned == True)
                & (Topic.is_deleted == False)
                & distillate_condition
            )
            .order_by(Topic.post_date)
        )
        condition = (
            (Topic.is_pinned == False)
            & (Topic.is_deleted == False)
            & distillate_condition
        )
        topics, total = get_topics(condition, pn, count)
        def get_topic_list():
            for I in pinned_topics:
                topic = I
                topic.tags = []
                yield topic
            for I in topics:
                yield I
        topic_list = get_topic_list()
    else:
        condition = (
            (Topic.is_deleted == False)
            & distillate_condition
        )
        topic_list, total = get_topics(
            condition, pn, count, tag=tag_slug
        )
    form = TopicAddForm()
    tag_list = [tag for tag in Tag.select()]
    form.tags.choices = [(tag.slug, tag.name) for tag in tag_list]
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash(_('Please sign in before publishing a topic.'), 'err')
            return redirect(url_for('user.login', next=request.url))
        if current_user.is_banned:
            flash(_('You are being banned.'), 'err')
            return redirect(request.url)
        title = form.title.data
        content = form.content.data
        tags = form.tags.data
        date_now = now()
        new_topic = Topic.create(
            author_id = current_user.id,
            title = title,
            summary = '',
            post_date = date_now,
            last_reply_date = date_now,
            last_reply_author_id = current_user.id
        )
        TagRelation.create(topic=new_topic, tag=None)
        with db.atomic():
            for tag in tags:
                found = find_record(Tag, slug=tag)
                # deleted/renamed tag?
                if found:
                    TagRelation.create(
                        topic=new_topic, tag=found
                    )
        first_post = create_post(
            new_topic, None, content, add_reply_count=False
        )
        new_topic.summary, new_topic.summary_images = (
            gen_summary(first_post.content)
        )
        new_topic.save()
        tieba_publish_topic(new_topic)
        flash(_('Topic published successfully.'), 'ok')
        return redirect(request.url)
    return render_template(
        'forum/topic_list.html',
        form = form,
        is_index = is_index,
        distillate_only = distillate_only,
        tag = tag_record,
        tag_list = tag_list,
        topic_list = topic_list,
        pn = pn,
        count = count,
        total = total
    )


def filter_deleted_post(post_list):
    deleted_id = -1
    for post in post_list:
        if deleted_id != -1 and post.path.find('/%d/' % deleted_id) != -1:
            continue
        else:
            if post.is_deleted:
                deleted_id = post.id
                continue
            else:
                yield post


@forum.route('/topic/<int:tid>', methods=['GET', 'POST'])
def topic_content(tid):
    def get_subpost_count(post):
        # only count direct child node
        return (
            Post
            .select()
            .where(
                Post.parent == post,
                Post.is_deleted == False
            )
        ).count()
    def gen_subpost_list(post):
        return filter_deleted_post(
            Post
            .select(Post, User)
            .join(User)
            .where(
                Post.path % (post.path+'/'+DB_WILDCARD)
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
            if current_user.is_banned:
                flash(_('You are being banned.'), 'err')
                return redirect(request.url)
            new_post = create_post(topic, None, form.content.data)
            tieba_publish_post(new_post)
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


@forum.route('/topic/tag-manage/<int:tid>', methods=['GET', 'POST'])
@privilege_required()
def topic_tag_manage(tid):
    topic = find_record(Topic, id=tid)
    if topic and not topic.is_deleted:
        form = TopicTagManageForm()
        tags_all = [tag for tag in Tag.select()]
        form.tags.choices = [(tag.slug, tag.name) for tag in tags_all]
        current_tags_slug = {
            relation.tag.slug: True
            for relation in (
                    TagRelation
                    .select(TagRelation, Tag)
                    .join(Tag)
                    .where(TagRelation.topic == topic)
            )
        }
        if form.validate_on_submit():
            with db.atomic():
                for rel in find_record_all(TagRelation, topic=topic):
                    rel.delete_instance()
                for tag in form.tags.data:
                    TagRelation.create(
                        topic=topic, tag=find_record(Tag, slug=tag)
                    )
            flash(_('Tags changed successfully.'))
            return redirect(url_for('.topic_content', tid=tid))
        return render_template(
            'forum/topic_tag_manage.html',
            form=form,
            tags_all = tags_all,
            current_tags_slug = current_tags_slug
        )
    else:
        abort(404)


@forum.route('/topic/set/pin/<int:tid>')
@privilege_required(admin=True)
def topic_pin(tid):
    revert = bool(request.args.get('revert'))
    topic = find_record(Topic, id=tid)
    if topic and not topic.is_deleted:
        if not revert:
            topic.is_pinned = True
            topic.save()
            flash(_('Topic pinned successfully.'), 'ok')
        else:
            topic.is_pinned = False
            topic.save()
            flash(_('Topic unpinned successfully.'), 'ok')
        return redirect(url_for('.topic_content', tid=tid))
    else:
        abort(404)


@forum.route('/topic/set/distillate/<int:tid>')
@privilege_required(admin=True)
def topic_distillate(tid):
    revert = bool(request.args.get('revert'))
    topic = find_record(Topic, id=tid)
    if topic and not topic.is_deleted:
        if not revert:
            topic.is_distillate = True
            topic.save()
            flash(_('Distillate added successfully.'), 'ok')
        else:
            topic.is_distillate = False
            topic.save()
            flash(_('Distillate removed successfully.'), 'ok')
        return redirect(url_for('.topic_content', tid=tid))
    else:
        abort(404)


@forum.route('/topic/remove/<int:tid>', methods=['GET', 'POST'])
@privilege_required()
def topic_remove(tid):
    topic = find_record(Topic, id=tid)
    if topic and not topic.is_deleted:
        if request.form.get('confirmed'):
            topic.is_deleted = True
            topic.save()
            DeleteRecord.create(
                topic=topic, date=now(), operator_id=current_user.id
            )
            create_system_message(
                (
                    _('Your topic {0} has been deleted by moderator {1}.\nThe title of your topic is {2}.')
                    .format(tid, current_user.name, topic.title)
                ),
                topic.author
            )
            flash(_('Topic deleted successfully.'), 'ok')            
            return redirect(url_for('index'))
        else:
            return render_template(
                'confirm.html',
                text = _('Are you sure to delete this topic?'),
                url_no = url_for('.topic_content', tid=tid)
            )
    else:
        abort(404)


@forum.route('/topic/revert/<int:tid>')
@privilege_required()
def topic_revert(tid):
    topic = find_record(Topic, id=tid)
    if topic and topic.is_deleted:
        topic.is_deleted = False
        topic.save()
        DeleteRecord.create(
            topic=topic,
            date=now(),
            is_revert=True,
            operator_id=current_user.id
        )
        create_system_message(
            (
                _('Your deleted topic {0} has been reverted by moderator {1}.\n{2}')
                .format(
                    tid, current_user.name, TID_SIGN + str(tid)
                )
            ),
            topic.author
        )
        flash(_('Topic reverted successfully.'), 'ok')
        return redirect(url_for('moderate.delete_record'))
    else:
        abort(404)


@forum.route('/post/<int:pid>', methods=['GET', 'POST'])
def post(pid):
    post = find_record(Post, id=pid)
    if post and post.is_available:
        if post.is_pm:
            abort(403)
        form = PostAddForm()
        if form.validate_on_submit():
            if post.is_sys_msg:
                abort(403)
            if not current_user.is_authenticated:
                flash(_('Please sign in before publishing a post.'), 'err')
                return redirect(url_for('user.login', next=request.url)) 
            if current_user.is_banned:
                flash(_('You are being banned.'), 'err')
                return redirect(request.url)           
            new_post = create_post(
                post.topic, post, form.content.data, is_pm=post.is_pm
            )
            if not post.is_pm:
                tieba_publish_subpost(new_post)
            flash(_('Reply published successfully.'))
            return redirect(url_for('.post', pid=pid))
        if not post.is_sys_msg:
            posts = (
                Post
                .select(Post, User)
                .join(User)
                .where(
                    (
                        (Post.path % (post.path+'/'+DB_WILDCARD))
                        | (Post.id == pid)
                    )
                )
                .order_by(Post.sort_path)
            )
            post_list = filter_deleted_post(posts)
        else:
            # system message
            post_list = [post]
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
    if post and post.is_available:
        if current_user.id != post.author.id:
            abort(401)
        if post.is_sys_msg:
            abort(403)
        form = PostAddForm(obj=post)
        if form.validate_on_submit():
            if not current_user.is_authenticated:
                flash(_('Please sign in before editing a post.'), 'err')
                return redirect(url_for('user.login', next=request.url))
            form.populate_obj(post)
            post.last_edit_date = now()
            post.save()
            if post.ordinal == 1 and not post.parent and post.topic:
                post.topic.summary, post.topic.summary_images = (
                    gen_summary(form.content.data)
                )
                post.topic.save()
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
    if post and post.is_available:
        if post.is_sys_msg or post.is_pm:
            abort(403)
        cancel_url = request.args.get('prev') or url_for('.post', pid=pid)
        if cancel_url.find(url_for('.post', pid=pid)) != -1: 
            if post.parent:
                ok_url = url_for('.post', pid=post.parent.id)
            else:
                ok_url = url_for('.topic_content', tid=post.topic.id)
        else:
            ok_url = cancel_url
        if request.form.get('confirmed'):
            post.is_deleted = True
            post.save()
            DeleteRecord.create(
                post=post, date=now(), operator_id=current_user.id
            )
            create_system_message(
                (
                    _('Your post {0} has been deleted by moderator {1}.\nThe content of your post is shown below:\n\n{2}')
                    .format(pid, current_user.name, post.content)
                ),
                post.author
            )
            flash(_('Post deleted successfully.'), 'ok')
            return redirect(ok_url)
        else:
            return render_template(
                'confirm.html',
                text = _('Are you sure to delete this post?'),
                url_no = cancel_url
            )
    else:
        abort(404)


@forum.route('/post/revert/<int:pid>')
@privilege_required()
def post_revert(pid):
    post = find_record(Post, id=pid)
    if post and post.is_deleted:
        if post.is_sys_msg or post.is_pm:
            abort(403)
        post.is_deleted = False
        post.save()
        DeleteRecord.create(
            post=post, date=now(), is_revert=True, operator_id=current_user.id
        )
        create_system_message(
            (
                _('Your deleted post {0} has been reverted by moderator {1}.\n{2}')
                .format(
                    pid, current_user.name, PID_SIGN + str(pid)
                )
            ),
            post.author
        )
        flash(_('Post reverted successfully.'), 'ok')
        return redirect(url_for('moderate.delete_record'))
    else:
        abort(404)
