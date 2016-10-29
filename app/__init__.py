# -*- coding: utf-8 -*-
import os
from flask import Flask, request, session
#from flask_babel import Babel, lazy_gettext
from peewee import SqliteDatabase
from config import config

db = SqliteDatabase('data-dev.db') # TODO create database
#babel = Babel()
#ext1 = Ext1()

def create_app(config_name):
    '''初始化App和扩展类'''
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    #db.init_app(app)  # 用数据库相关 Flask 扩展可实现工厂模式载入
    #babel.init_app(app)
    #ext1.init_app(app)
    #......

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    #from .auth import auth as auth_blueprint
    #app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .api_1_0 import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api/1.0')

    return app
