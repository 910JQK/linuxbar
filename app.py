#!/usr/bin/env python3


import os
from flask import Flask
from flask_babel import Babel
from flask_login import current_user


from models import Config
from user import user, login_manager


app = Flask(__name__)
babel = Babel(app)
login_manager.init_app(app)
app.register_blueprint(user, url_prefix='/user')
DEBUG = True


@app.context_processor
def inject_data():
    def get_config(name):
        return Config.get(name)
    return dict(get_config=get_config)


@app.route('/')
def index():
    # just for testing
    html = '<!DOCTYPE html><title>Test</title><h1>It just works, but very ugly.</h1>'
    if current_user.is_authenticated:
        html += '<div><span>%d</span><span>%s</span><a href="/user/logout">Logout</a></div>' % current_user.id, current_user.name
    else:
        html += '<div><a target="_blank" href="/user/register">Register</a></div>'
        html += '<div><a target="_blank" href="/user/login">Sign in</a></div>'
    return html


def main():
    app.secret_key = os.urandom(24)
    app.run(debug=DEBUG)


if __name__ == '__main__':
    main()
