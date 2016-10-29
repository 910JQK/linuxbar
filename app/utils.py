import hashlib
import smtplib
import datetime
import threading
from collections import namedtuple
from urllib.parse import quote
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Response, jsonify
import json

now = datetime.datetime.now


def json_response(result):
    '''Generate JSON responses from the return values of functions of forum.py
    @param tuple result (int, str[, dict])
    @return Response
    '''
    formatted_result = {'code': result[0],
                        'msg': result[1]
                       }
    if len(result) == 3 and result[2]:
        formatted_result['data'] = result[2]
    return Response(json.dumps(formatted_result), mimetype='application/json')


# reserved for l10n
def _(string):
    return string


def md5(string):
    return hashlib.md5(bytes(string, encoding='utf8')).hexdigest()


def sha256(string):
    return hashlib.sha256(bytes(string, encoding='utf8')).hexdigest()


def url_quote(text):
    return quote(text, encoding='utf8')


class EmailThread(threading.Thread):
    def __init__(self, subject, addr_from, addr_to, content, html=''):
        if(html):
            msg = MIMEMultipart('alternative')
            msg_plaintext = MIMEText(content, 'plain')
            msg_html = MIMEText(html, 'html')
            msg.attach(msg_html)
            msg.attach(msg_plaintext)
            msg = msg
        else:
            msg = MIMEText(content, 'plain')
        msg['Subject'] = subject
        msg['From'] = addr_from
        msg['To'] = addr_to
        self.msg = msg
        threading.Thread.__init__(self)

    def run (self):
        smtp = smtplib.SMTP('localhost')
        smtp.send_message(self.msg)
        smtp.quit()


def send_mail(subject, addr_from, addr_to, content, html=''):
    '''Send an HTML email

    @param str subject
    @param str addr_from
    @param str addr_to
    @param str content
    @return void
    '''
    EmailThread(subject, addr_from, addr_to, content, html).start()
