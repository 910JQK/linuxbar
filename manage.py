#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from app import create_app, db
from app.models import tables, Config
from app.utils import _
from flask_script import Manager, Shell

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)

# Global variables to jinja2 environment
app.jinja_env.globals['_'] = _
#app.jinja_env.filters['split'] = split


def make_shell_context():
    '''定义向Shell导入的对象'''
    return dict(app=app, db=db)
manager.add_command("shell", Shell(make_context=make_shell_context))


@manager.command
def test():
    '''Run the unit tests'''
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)


@manager.command
def init_db():
    '''Initial database'''
    db.connect()

    print('Creating tables ...')
    db.create_tables(tables)
    print('Tables have been created.')

    print('Writing default configurations ...')
    Config.create(name='site_name', value=app.config['DEFAULT_SITE_NAME'])
    Config.create(name='site_url', value=app.config['DEFAULT_SITE_URL'])
    Config.create(name='count_topic', value=app.config['DEFAULT_TOPICS_PER_PAGE'])
    Config.create(name='count_post', value=app.config['DEFAULT_POSTS_PER_PAGE'])
    Config.create(name='count_list_item', value=app.config['DEFAULT_LIST_ITEM_PER_PAGE'])
#   Config.create(name='count_subpost', value=app.config['DEFAULT_SUBPOSTS_PER_PAGE'])
    print('Default configurations have been written into database.')

    db.close()


if __name__ == '__main__':
    manager.run()
