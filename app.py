#!/usr/bin/env python3


import os
import io
import hashlib
import datetime
from flask import Flask, Response, session
from flask_babel import Babel
from flask_login import current_user
from flask_wtf.csrf import CsrfProtect


import captcha
from utils import _
from models import Config
from user import user, login_manager


app = Flask(__name__)
babel = Babel(app)
login_manager.init_app(app)
CsrfProtect(app)
app.register_blueprint(user, url_prefix='/user')
DEBUG = True


@app.context_processor
def inject_data():
    return {'get_config': Config.Get}


@app.template_filter('md5')
def md5(string):
    return hashlib.md5(bytes(string, encoding='utf8')).hexdigest()


@app.template_filter('date')
def format_date(date, detailed=False):
    # behaviour of this function must be consistent with the front-end
    if detailed:
        return date.isoformat(' ');
    delta = round((datetime.datetime.now() - date).total_seconds())
    if delta < 60:
        return _('just now')
    elif delta < 3600:
        minutes = delta / 60
        if minutes == 1:
            return _('a minute ago')
        else:
            return _('%d minutes ago') % minutes
    elif delta < 86400:
        hours = delta / 3600
        if hours == 1:
            return _('an hour ago')
        else:
            return _('%d hours ago') % hours
    # 604800 = 86400*7
    elif delta < 604800:
        days = delta / 86400
        if days == 1:
            return _('a day ago')
        else:
            return _('%d days ago') % days
    # 2629746 = 86400*(31+28+97/400+31+30+31+30+31+31+30+31+30+31)/12
    elif delta < 2629746:
        weeks = delta / 604800
        if weeks == 1:
            return _('a week ago')
        else:
            return _('%d weeks ago') % weeks
    # 31556952 = 86400*(365+97/400)
    elif delta < 31556952:
        months = delta / 2629746
        if months == 1:
            return _('a month ago')
        else:
            return _('%d months ago') % months
    else:
        years = delta / 31556952
        if years == 1:
            return _('a year ago')
        else:
            return _('%d years ago') % years


@app.route('/')
def index():
    # just for testing
    html = '<!DOCTYPE html><title>Test</title><h1>It just works, but very ugly.</h1>'
    if current_user.is_authenticated:
        html += '<div><span>%d</span><span> / </span><span>%s</span></div><div><a href="/user/logout">Logout</a></div>' % (current_user.id, current_user.name)
    else:
        html += '<div><a target="_blank" href="/user/register">Register</a></div>'
        html += '<div><a target="_blank" href="/user/login">Sign in</a></div>'
        html += '<div><a target="_blank" href="/user/get-token">Reset Password</a></div>'
    return html


@app.route('/get-captcha')
def get_captcha():
    code = captcha.gen_captcha()
    session['captcha'] = code.lower()
    image = captcha.gen_image(code)
    output = io.BytesIO()
    image.save(output, format='PNG')
    image_data = output.getvalue()
    return Response(image_data, mimetype='image/png')


def main():
    app.secret_key = b'\xe9\xd3\x8fV0n\xcajX~P%*\xf1=O\xb7\xbc\xfa\xe5\xf5db'
    app.run(debug=DEBUG)


if __name__ == '__main__':
    main()
