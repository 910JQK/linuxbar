from flask import Blueprint, session, request, flash, redirect, render_template, url_for, abort
from flask_login import current_user
from werkzeug.datastructures import MultiDict
from peewee import JOIN
from collections import namedtuple
import datetime


from utils import _
from utils import *
from user import privilege_required
from post import create_system_message
from forms import ConfigEditForm, TagEditForm
from models import Config, Tag, Ban, User, DeleteRecord, Topic, Post


moderate = Blueprint(
    'moderate', __name__, template_folder='templates', static_folder='static'
)


@moderate.route('/config', methods=['GET', 'POST'])
@privilege_required(admin=True)
def config():
    config_dict = {}
    for item in Config.select():
        config_dict[item.name] = item.value
    Struct = namedtuple('config', [*config_dict])
    config_obj = Struct(**config_dict)

    form = ConfigEditForm(obj=config_obj)
    if form.validate_on_submit():
        for item_name in config_dict:
            (
                Config
                .update(value = getattr(form, item_name).data)
                .where(Config.name == item_name)
                .execute()
            )
        flash(_('Site config updated successfully.'), 'ok')
    return render_template('moderate/config.html', form=form)


@moderate.route('/tag/list', methods=['GET', 'POST'])
@privilege_required()
def tag_list():
    all_tags = Tag.select()
    form = TagEditForm()
    if form.validate_on_submit():
        if (
                not find_record(Tag, slug=form.slug.data)
                and not find_record(Tag, name=form.name.data)
        ):
            tag = Tag()
            form.populate_obj(tag)
            tag.save(force_insert=True)
            flash(_('Tag %s created successfully.') % tag.name, 'ok')
        else:
            flash(_('Naming conflict detected.'), 'err')
        return redirect(url_for('.tag_list'))
    return render_template(
        'moderate/tag_list.html', form=form, all_tags=all_tags
    )


@moderate.route('/tag/edit/<int:tag_id>', methods=['GET', 'POST'])
@privilege_required()
def tag_edit(tag_id):
    tag = find_record(Tag, id=tag_id)
    if tag:
        form = TagEditForm(obj=tag)
        if form.validate_on_submit():
            if (
                    not Tag.select().where(
                        (Tag.id != tag_id)
                        & (
                            (Tag.slug == form.slug.data)
                            | (Tag.name == form.name.data)
                        )
                    )
            ):
                form.populate_obj(tag)
                tag.save()
                flash(_('Edit on tag %s saved successfully.') % tag.name, 'ok')
                return redirect(url_for('.tag_list'))
            else:
                flash(_('Naming conflict detected.'), 'err')
        return render_template('moderate/tag_edit.html', form=form)
    else:
        abort(404)


@moderate.route('/tag/remove/<int:tag_id>', methods=['GET', 'POST'])
@privilege_required()
def tag_remove(tag_id):
    tag = find_record(Tag, id=tag_id)
    if tag:
        if request.form.get('confirmed'):
            tag.delete_instance()
            flash(_('Tag %s deleted successfully.') % tag.name, 'ok')
            return redirect(url_for('.tag_list'))
        else:
            return render_template(
                'confirm.html',
                text = _('Are you sure to delete tag %s ?') % tag.name,
                url_no = url_for('.tag_list')
            )
    else:
        abort(404)


@moderate.route('/ban/list')
@privilege_required()
def ban_list():
    pn = int(request.args.get('pn', '1'))
    count = int(Config.Get('count_item'))
    bans = (
        Ban
        .select(Ban, User)
        .join(User)
    )
    total = bans.count()
    ban_list = bans.order_by(Ban.date.desc()).paginate(pn, count)
    return render_template(
        'moderate/ban_list.html',
        pn = pn,
        count = count,
        total = total,
        ban_list = ban_list
    )


@moderate.route('/ban/revert/<int:ban_id>', methods=['GET', 'POST'])
@privilege_required()
def ban_remove(ban_id):
    ban = find_record(Ban, id=ban_id)
    if ban and ban.is_valid:
        if request.form.get('confirmed'):
            ban.delete_instance()
            create_system_message(
                (
                    _('The ban on you has been cancelled by moderator {0}')
                    .format(current_user.name)
                ),
                ban.user
            )
            flash(
                _('Ban on user %s reverted successfully.') % ban.user.name,
                'ok'
            )
            return redirect(url_for('.ban_list'))
        else:
            return render_template(
                'confirm.html',
                text = (
                    _('Are you sure to revert ban on user %s ?')
                    % ban.user.name
                ),
                url_no = url_for('.ban_list')
            )
    else:
        flash(_('No such ban record.'))
        return redirect(url_for('.ban_list'))


@moderate.route('/delete-record')
@privilege_required()
def delete_record():
    pn = int(request.args.get('pn', '1'))
    count = int(Config.Get('count_item'))
    records = (
        DeleteRecord
        .select(DeleteRecord, User, Topic, Post)
        .join(User)
        .switch(DeleteRecord)
        .join(Topic, JOIN.LEFT_OUTER)
        .switch(DeleteRecord)
        .join(Post, JOIN.LEFT_OUTER)
    )
    total = records.count()
    rec_list = records.order_by(DeleteRecord.date.desc()).paginate(pn, count)
    return render_template(
        'moderate/delete_record.html',
        pn = pn,
        count = count,
        total = total,
        rec_list = rec_list
    )


@moderate.route('/moderator-list')
@privilege_required()
def moderator_list():
    pn = int(request.args.get('pn', '1'))
    count = int(Config.Get('count_item'))
    moderators = (
        User
        .select()
        .where(User.level > 0)
    )
    total = moderators.count()
    moderator_list = (
        moderators.order_by(User.date_register.desc()).paginate(pn, count)
    )
    return render_template(
        'moderate/moderator_list.html',
        pn = pn,
        count = count,
        total = total,
        moderator_list = moderator_list
    )


