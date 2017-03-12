from flask import Blueprint, session, request, flash, redirect, render_template, url_for, abort
from flask_login import current_user, login_required


from utils import _
from utils import *
from forms import TiebaSyncForm
from models import User, TiebaUser


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
            flash(_('Sync stopped successfully.'), 'ok')
        return redirect(url_for('.sync_settings'))
    else:
        return render_template(
            'confirm.html',
            text = _('Are you sure to stop sync between Tieba ?'),
            url_no = url_for('.sync_settings')
        )
