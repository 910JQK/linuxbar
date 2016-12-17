DB_WILDCARD = '*' # SQLite = *, others = %


DEFAULT_CONFIG = {
    'site_name': 'Linuxbar',
    'site_url': 'http://127.0.0.1:5000',
    'mail_addr': 'no_reply@foo.bar',
    'count_topic': '30',
    'count_post': '25',
    'count_cut': '4',
    'count_item': '15'
}


DEBUG = True
SECRET_KEY = b'\xe9\xd3\x8fV0n\xcajX~P%*\xf1=O\xb7\xbc\xfa\xe5\xf5db'
TOKEN_LIFETIME = 20 # minutes
SUMMARY_LENGTH = 60 # in [4, 128] (128 = Topic.summary.max_length / 4)
BAN_DAYS = [1, 3, 10, 30, 100]


LINK_PROTOCOLS = ['http', 'https', 'ftp']
CODE_BEGIN = '/***#'
CODE_END = '#***/'
INLINE_CODE_SIGN = '`' # a single char
NOTIFICATION_SIGN = '@' # a single char
IMAGE_SIGN = '%' # a single char
FORMAT_SIGN = '**'
FORMAT_DEFAULT = '*'
FORMATS = {
    '*': 'b',
    '~': 'i',
    '!': 'del'
    # a single char: tag name
}


UPLOAD_FOLDER = 'upload'
MAX_UPLOAD_SIZE = 5 * 1024 * 1024
IMAGE_MIME = {'png': 'image/png', 'jpeg': 'image/jpeg', 'gif': 'image/gif'}
