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
from pipeline import get_content_html
from user import user, login_manager
from moderate import moderate
from image import image
from forum import forum, topic_list
from config import DEBUG, SECRET_KEY, UPLOAD_FOLDER, MAX_UPLOAD_SIZE


app = Flask(__name__)
babel = Babel(app)
login_manager.init_app(app)
CsrfProtect(app)
app.register_blueprint(user, url_prefix='/user')
app.register_blueprint(moderate, url_prefix='/moderate')
app.register_blueprint(image, url_prefix='/image')
app.register_blueprint(forum, url_prefix='/forum')
DEBUG = True


@app.context_processor
def inject_data():
    return {'get_config': Config.Get}


app.add_template_filter(md5, 'md5')
app.add_template_filter(format_date, 'date')
app.add_template_filter(path_get_level, 'get_level')
app.add_template_filter(path_get_padding, 'get_padding')
app.add_template_filter(get_content_html, 'get_html')


@app.route('/', methods=['GET', 'POST'])
def index():
    return topic_list(tag_slug='')


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
