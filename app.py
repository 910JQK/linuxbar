#!/usr/bin/env python3


from flask import Flask, Response, request
app = Flask(__name__)

import json
import smtplib
from email.mime.text import MIMEText

import forum
from validation import *


# Enable debug mode for test
DEBUG = True
EMAIL_ADDRESS = 'no_reply@foo.bar'


def _(string):
    return string # reserved for l10n


def send_mail(subject, addr_from, addr_to, content):
    msg = MIMEText(content)
    msg['Subject'] = subject
    msg['From'] = addr_from
    msg['To'] = addr_to
    smtp = smtplib.SMTP('localhost')
    smtp.send_message(msg)
    smtp.quit()


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


@app.route('/api/user/register', methods=['POST'])
def user_register():
    mail = request.form['mail']
    name = request.form['name']
    # unencrypted password: TLS is necessary
    password = request.form['password']

    try:
        validate_email(_('Mail address'), mail)
        validate(_('Username'), name, min=3, max=32)
        validate(_('Password'), password, not_empty=True)
    except ValidationError as err:
        return validation_err_response(err)

    result = forum.user_register(mail, name, password)
    if(result[0] != 0):
        return json_response(result)
    data = result[2]

    config_result = forum.config_get()
    if(config_result[0] != 0):
        return json_response(config_result)
    config = config_result[2]

    site_name = config['site_name']
    site_url = config['site_url']
    activation_url = (
        '%s/api/user/activate/%d/%s' % (
            site_url,
            data['uid'],
            data['activation_code']
        )
    )
    # remove info of activation code (very important !!!)
    del data['activation_code']
    send_mail(
        subject = 'Activation Mail of %s' % site_name,
        addr_from = EMAIL_ADDRESS,
        addr_to = mail,
        content = activation_url
    )

    return json_response(result)


@app.route('/api/user/activate/<int:uid>/<code>')
def user_activate(uid, code):
    # TODO: change into a page, not API returning unfriendly JSON.
    # And don't forget to change URL sent above.
    try:
        validate_sha256(_('Activation Code'), code)
    except ValidationError as err:
        return validation_err_response(err)
    return json_response(forum.user_activate(uid, code))


if __name__ == '__main__':
    app.run(debug=DEBUG)
