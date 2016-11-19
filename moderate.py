from flask import Blueprint, session, request, flash, redirect, render_template, url_for, abort
from flask_login import current_user
from werkzeug.datastructures import MultiDict
from collections import namedtuple


from utils import _
from user import privilege_required
from forms import ConfigEditForm#, TagAddForm, TagEditForm
from models import Config, Tag


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
