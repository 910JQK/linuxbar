# -*- coding: utf-8 -*-
from flask import Blueprint

main = Blueprint('main', __name__)

from . import views
from .views import config

@main.app_context_processor
def inject_data():
    return dict(config=config)
