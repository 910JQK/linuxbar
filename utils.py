import random
import hashlib
import datetime
import threading
from html import escape
from urllib.parse import quote


import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


from config import SUMMARY_LENGTH


TOKEN_CHARS = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'


now = datetime.datetime.now


# reserved for l10n
def _(string, string_pl=None, n=None):
    if not string_pl:
        return string
    else:
        if n == 1:
            return string
        else:
            return string_pl


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


def gen_summary(content):
    if len(content) > SUMMARY_LENGTH:
        return content[:SUMMARY_LENGTH-3] + '...'
    else:
        return content


def path_get_level(path):
    return (len(path.split('/')) - 2)


def path_get_padding(level):
    x = level-1
    if x == -1:
        return 0
    elif x <= 5:
        # current = 1 - 0.1*x (x >= 0)
        return (x+1)*(2-x/10)/2
    elif x > 5 and x < 28:
        return 4.5 + 0.25*(x-5)
    else:
        return 10


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
