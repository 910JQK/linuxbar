#!/usr/bin/env python3


from flask import Flask, Response
app = Flask(__name__)

import json
import smtplib
from email.mime.text import MIMEText

import forum
from validation import *


def _(string):
    return string # reserved for l10n


def json_response(result):
    '''Generate JSON responses from the return values of functions of forum.py

    @param tuple result
    @return Response
    '''
    formatted_result = {'code': result[0], 'msg': result[1]}
    if(len(result) == 3):
        formatted_result['data'] = result[2]
    return Response(json.dumps(formatted_result), mimetype='application/json')


def validation_err_response(err):
    '''Generate responses for validation errors

    @param ValidationError err
    @return Response
    '''
    return json_response((255, _('Validation error: %s' % str(err)) ) )


@app.route('/')
def index():
    return '<h1>It just works, but very ugly.</h1>'


@app.route('/api/user/get/name/<int:uid>')
def user_get_name(uid):
    return json_response(forum.user_get_name(uid))


@app.route('/api/user/get/uid/<name>')
def user_get_uid(name):
    try:
        validate(_('Name'), name, min=3, max=32)
    except ValidationError as err:
        return validation_err_response(err)
    return json_response(forum.user_get_uid(name))


if __name__ == '__main__':
    app.run()
