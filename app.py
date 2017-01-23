#!/usr/bin/env python3


import os
import io
import hashlib
import datetime
from flask import Flask, Response, session, render_template
from flask_babel import Babel
from flask_login import current_user
from flask_wtf.csrf import CsrfProtect


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
    DEBUG, SECRET_KEY, UPLOAD_FOLDER, MAX_UPLOAD_SIZE, assert_config,
    RICHTEXT_INFO, RICHTEXT_INFO_JSON
)


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
    def get_faces():
        return Face.select().order_by(Face.name)
    return {
        'get_config': Config.Get,
        'get_faces': get_faces,
        'RT_INFO': RICHTEXT_INFO_JSON
    }


app.add_template_filter(md5, 'md5')
app.add_template_filter(format_date, 'date')
app.add_template_filter(get_color, 'get_color')
app.add_template_filter(path_get_level, 'get_level')
app.add_template_filter(path_get_padding, 'get_padding')
app.add_template_filter(get_content_html, 'get_html')
app.add_template_filter(filter_deleted_post, 'filter_deleted_post')


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
    assert_config()
    gettext.install(
        'linuxbar',
        os.path.join(
            os.path.dirname(
                os.path.realpath(
                    __file__
                )
            ),
            'locale'
        )
    )
    app.secret_key = SECRET_KEY
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE
    app.run(debug=DEBUG)


if __name__ == '__main__':
    run()
