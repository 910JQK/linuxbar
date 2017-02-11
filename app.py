#!/usr/bin/env python3


import os
import io
import json
import hashlib
import datetime
from flask import Flask, Response, session, render_template
from flask_login import current_user
from flask_wtf.csrf import CsrfProtect
from flask_babel import Babel


import captcha
from utils import _
from utils import *
from models import Config, Face
from pipeline import get_content_html
from user import user, login_manager
from moderate import moderate
from image import image
from forum import forum, topic_list, filter_deleted_post
from config import (
    PREFIX_ENABLED, PREFIX, DEBUG, SECRET_KEY, UPLOAD_FOLDER, MAX_UPLOAD_SIZE, 
    RICHTEXT_INFO, RICHTEXT_INFO_JSON, assert_config
)


class PrefixMiddleware(object):
    def __init__(self, app, prefix=''):
        self.app = app
        self.prefix = prefix
    def __call__(self, environ, start_response):
        #environ['PATH_INFO'] = environ['PATH_INFO'][len(self.prefix):]
        environ['SCRIPT_NAME'] = self.prefix
        return self.app(environ, start_response)


app = Flask(__name__)

assert_config()
app.secret_key = SECRET_KEY
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE
app.config['BABEL_DEFAULT_LOCALE'] = LOCALE
if PREFIX_ENABLED:
    app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix=PREFIX)

babel = Babel(app)
login_manager.init_app(app)
CsrfProtect(app)

app.register_blueprint(user, url_prefix='/user')
app.register_blueprint(moderate, url_prefix='/moderate')
app.register_blueprint(image, url_prefix='/image')
app.register_blueprint(forum, url_prefix='/forum')

app.add_template_filter(md5, 'md5')
app.add_template_filter(format_date, 'date')
app.add_template_filter(get_color, 'get_color')
app.add_template_filter(path_get_level, 'get_level')
app.add_template_filter(path_get_padding, 'get_padding')
app.add_template_filter(get_content_html, 'get_html')
app.add_template_filter(filter_deleted_post, 'filter_deleted_post')
app.add_template_filter(filter_append_time, 'append_time')


@app.context_processor
def inject_data():
    def get_faces():
        return Face.select().order_by(Face.name)
    if LOCALE:
        with open(
            os.path.join(
                'translations', LOCALE, 'LC_MESSAGES', 'messages.json'
            )
        ) as f:
            frontend_trans = f.read()
            try:
                json.loads(frontend_trans)
            except json.decoder.JSONDecodeError:
                raise AssertionError(
                    'Front-end translation file has a wrong format.'
                )
    else:
        frontend_trans = '{}'
    return {
        'get_config': Config.Get,
        'get_faces': get_faces,
        'RT_INFO': RICHTEXT_INFO_JSON,
        'FRONTEND_TRANS': frontend_trans 
    }


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


@app.route('/richtext-info')
def richtext_info():
    return render_template('richtext_info.html', info=RICHTEXT_INFO)


def run():
    app.run(debug=DEBUG)


if __name__ == '__main__':
    run()
