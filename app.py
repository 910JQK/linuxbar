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
from utils import *
from models import Config
from user import user, login_manager
from moderate import moderate
from image import image
from config import DEBUG, SECRET_KEY, UPLOAD_FOLDER, MAX_UPLOAD_SIZE


app = Flask(__name__)
babel = Babel(app)
login_manager.init_app(app)
CsrfProtect(app)
app.register_blueprint(user, url_prefix='/user')
app.register_blueprint(moderate, url_prefix='/moderate')
app.register_blueprint(image, url_prefix='/image')
DEBUG = True


@app.context_processor
def inject_data():
    return {'get_config': Config.Get}


app.add_template_filter(md5, 'md5')
app.add_template_filter(format_date, 'date')


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


def run():
    app.secret_key = SECRET_KEY
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE
    app.run(debug=DEBUG)


if __name__ == '__main__':
    run()
