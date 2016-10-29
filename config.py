# -*- coding: utf-8 -*-
import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    '''通用配置'''
    SECRET_KEY = os.getenv('SECRET_KEY') or 'secret_key_string'  # 用于加密 session 的密钥
    EMAIL_ADDRESS = 'no_reply@foo.bar'

    # Codepoints, must be greater than 3
    SUMMARY_LENGTH = 60

    # Fixed for positioning
    COUNT_SUBPOST = 10

    # String because input is string
    BAN_DAYS_LIST = ['1', '3', '10', '30']
    IMAGE_FORMATS = ['png', 'gif', 'jpeg']
    IMAGE_MIME = {'png': 'image/png', 'jpeg': 'image/jpeg', 'gif': 'image/gif'}

    # Upload config
    UPLOAD_FOLDER = 'upload'
    MAX_UPLOAD_LENGTH = 5 * 1024 * 1024

    # Site config
    DEFAULT_SITE_NAME = 'Linuxbar'
    DEFAULT_SITE_URL = 'http://127.0.0.1:5000'
    DEFAULT_TOPICS_PER_PAGE = '30'
    DEFAULT_POSTS_PER_PAGE = '25'
    DEFAULT_LIST_ITEM_PER_PAGE = '15'
    # in order to position a subpost, fixed value is required
    # DEFAULT_SUBPOSTS_PER_PAGE = '10'

    @staticmethod
    def init_app(app):
        '''初始化app'''
        pass


class DevelopmentConfig(Config):
    '''开发环境配置'''
    # Enable debug mode for test
    DEBUG = True
    DATABASE_URI = os.getenv('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-dev.db')


class TestingConfig(Config):
    '''测试环境配置'''
    TESTING = True
    DATABASE_URI = os.getenv('TEST_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-test.db')


class ProductionConfig(Config):
    '''生产环境配置'''
    DATABASE_URI = os.getenv('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data.db')


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,

    'default': DevelopmentConfig
}
