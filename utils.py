import hashlib
import datetime
import threading
from html import escape
from urllib.parse import quote
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


now = datetime.datetime.now


# reserved for l10n
def _(string):
    return string


def sha256(string):
    return hashlib.sha256(bytes(string, encoding='utf8')).hexdigest()


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
