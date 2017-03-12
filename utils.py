import os
import re
import random
import hashlib
import datetime
import threading
import gettext
from math import log
from html import escape
from urllib.parse import quote, unquote
from config import LOCALE


import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


import base64
from Crypto import Random
from Crypto.Cipher import AES


TOKEN_CHARS = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'


now = datetime.datetime.now


locale_path = os.path.join(
    os.path.dirname(
        os.path.realpath(
            __file__
        )
    ),
    'translations'
)
translation = gettext.translation('messages', locale_path, languages=[LOCALE])


def _(string, string_pl=None, n=None):
    if not string_pl:
        return translation.gettext(string)
    else:
        return translation.ngettext(string, string_pl, n)


def sha256(string):
    return hashlib.sha256(bytes(string, encoding='utf8')).hexdigest()


def md5(string):
    return hashlib.md5(bytes(string, encoding='utf8')).hexdigest()


def gen_token():
    return ''.join(random.choice(TOKEN_CHARS) for i in range(0, 16))


def url_quote(text):
    return quote(text, encoding='utf8')


def find_record_all(table, *args, **kwargs):
    query = table.select().where(
        *((getattr(table, field) == value) for field, value in kwargs.items())
    )
    for record in query:
        yield record


def find_record(table, *args, **kwargs):
    try:
        return find_record_all(table, *args, **kwargs).__next__()
    except StopIteration:
        return None


def path_get_level(path):
    return (len(path.split('/')) - 2)


def path_get_padding(level):
    # f(0) = 0, f(4) = 0.8 + 2.2 = 3
    return 0.8 + (2.2/log(1+4))*log(1+level)


def filter_append_time(string):
    return string + '?t=' + str(now().timestamp())


def get_color(string, saturation, lightness):
    hash_value = sha256(string)
    n256 = int(hash_value[0:2], 16)
    hue = int(round(360*(n256/256)))
    return 'hsl(%d, %d%%, %d%%)' % (hue, saturation, lightness)


def format_date(date, detailed=False):
    # behaviour of this function must be consistent with the front-end
    if detailed:
        return date.isoformat(' ');
    delta = int(round((datetime.datetime.now() - date).total_seconds()))
    if delta < 60:
        return _('just now')
    elif delta < 3600:
        minutes = delta // 60
        if minutes == 1:
            return _('a minute ago')
        else:
            return _('%d minutes ago') % minutes
    elif delta < 86400:
        hours = delta // 3600
        if hours == 1:
            return _('an hour ago')
        else:
            return _('%d hours ago') % hours
    # 604800 = 86400*7
    elif delta < 604800:
        days = delta // 86400
        if days == 1:
            return _('a day ago')
        else:
            return _('%d days ago') % days
    # 2629746 = 86400*(31+28+97/400+31+30+31+30+31+31+30+31+30+31)/12
    elif delta < 2629746:
        weeks = delta // 604800
        if weeks == 1:
            return _('a week ago')
        else:
            return _('%d weeks ago') % weeks
    # 31556952 = 86400*(365+97/400)
    elif delta < 31556952:
        months = delta // 2629746
        if months == 1:
            return _('a month ago')
        else:
            return _('%d months ago') % months
    else:
        years = delta // 31556952
        if years == 1:
            return _('a year ago')
        else:
            return _('%d years ago') % years


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
    EmailThread(subject, addr_from, addr_to, content, html).start()


class AESCipher(object):

    # http://stackoverflow.com/questions/12524994
    
    def __init__(self, key):
        self.bs = 32
        self.key = hashlib.sha256(key.encode(encoding='utf8')).digest()

    def encrypt(self, raw):
        raw = self._pad(quote(raw))
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return unquote(self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8'))

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]
