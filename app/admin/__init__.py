# TODO: web backend for manage

from flask import Blueprint

admin = Blueprint('admin', __name__)

from . import views, user
