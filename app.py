#!/usr/bin/env python3


from flask import Flask
from flask_babel import Babel


from user import user, login_manager


app = Flask(__name__)
babel = Babel(app)
login_manager.init_app(app)
app.register_blueprint(user)


@app.route('/')
def index():
    # just for testing
    html = '<!DOCTYPE html><h1>It just works, but very ugly.</h1>'
    if current_user.is_authenticated:
        html += '<div><a target="_blank" href="/user/register">Register</a></div>'
        html += '<div><a target="_blank" href="/user/login">Sign in</a></div>'
    else:
        html += '<div><span>%d</span><span>%s</span><a href="/user/logout">Logout</a></div>' % current_user.id, current_user.name
    return html
