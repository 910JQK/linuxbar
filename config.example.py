import os


DB_WILDCARD = '*' # SQLite = *, others = %


DEFAULT_CONFIG = {
    'site_name': 'Linuxbar',
    'site_url': 'http://127.0.0.1:5000',
    'mail_addr': 'no_reply@foo.bar',
    'count_topic': '30',
    'count_post': '25',
    'count_item': '15'
}


PREFIX_ENABLED = False
PREFIX = '/linuxbar'
LOCALE = 'zh_CN'
DEBUG = True
SECRET_KEY = b'\xe9\xd3\x8fV0n\xcajX~P%*\xf1=O\xb7\xbc\xfa\xe5\xf5db'
INACTIVE_USER_LIFETIME = 30 # minutes
TOKEN_LIFETIME = 20 # minutes
SUMMARY_LENGTH = 90 # in [4, 128] (128 = Topic.summary.max_length / 4)
THUMBNAIL_MAX_HEIGHT = 96 # pixels
BAN_DAYS = [1, 3, 10, 30, 100]


LINK_PROTOCOLS = ['http', 'https', 'ftp']
TIEBA_COMP = False
TIEBA_SYNC_ON = False
TIEBA_SYNC_KW = 'linux'
TIEBA_SYNC_INTERVAL = 300
TIEBA_SYNC_DELAY = 10
TIEBA_SYNC_OFFSET = 7
TIEBA_SYNC_PENDING_MAX = 15
TIEBA_SYNC_P = [
    1.0, # probability of sync when the topic list is accessed
    0.5, # a topic
    0.2  # a post
]
TIEBA_SUBMIT_URL = 'http://tieba.baidu.com/mo/m/submit'
TIEBA_M_URL = 'http://tieba.baidu.com/mo/m'
TIEBA_FLR_URL = 'http://tieba.baidu.com/mo/m/flr'
TIEBA_TIMG_URL = 'http://m.tiebaimg.com/timg?wapp&quality=100&size=b2000_2000'
TIEBA_EMOTICON_URL = 'http://tb2.bdstatic.com/tb/editor/images/'
CODE_BEGIN = '/***#'
CODE_END = '#***/'
PID_SIGN = 'p#'
TID_SIGN = 't#'
INLINE_CODE_SIGN = '`' # a single char
NOTIFICATION_SIGN = '@' # a single char
IMAGE_SIGN = '%%'
FACE_SIGN = '#'
IMAGE_LIMIT = 15
FACE_LIMIT = 20
FORMAT_SIGN = '**'
FORMAT_DEFAULT = '*' # a single char
FORMATS = {
    '*': 'b',
    '~': 'i',
    '!': 'del'
    # a single char: tag name
}
RICHTEXT_INFO = '''
<p><b>Bold</b>: <code>***bold**</code> or <code>**bold**</code></p>
<p><i>Italic</i>: <code>**~italic**</code></p>
<p><del>Mask</del>: <code>**!Mask**</code></p>
<p><code>Inline Code</code>: <code>`Inline Code`</code></p>
<p>Image: <code>%%hash</code></p>
<p>Face: <code>#name</code></p>
<div class="highlight"><pre>
Code Box:
/***# language
code
code
code
#***/
</pre>
</div>
'''
RICHTEXT_INFO_JSON = '''
{
  "formats": [
    ["bold", "**", "**"],
    ["italic", "**~", "**"],
    ["mask", "**!", "**"],
    ["inline_code", "`", "`"]    
  ],
  "image_prefix": "%%",
  "face_prefix": "#",
  "code_prefix": "/***#",
  "code_suffix": "#***/"
}
'''


UPLOAD_FOLDER = 'upload'
MAX_UPLOAD_SIZE = 7 * 1024 * 1024
IMAGE_MIME = {'png': 'image/png', 'jpeg': 'image/jpeg', 'gif': 'image/gif'}


def assert_config():
    assert os.path.isdir(UPLOAD_FOLDER)
    assert SUMMARY_LENGTH in range(4, 128+1)
    assert len(INLINE_CODE_SIGN) == 1
    assert len(NOTIFICATION_SIGN) == 1
    assert len(FORMAT_DEFAULT) == 1
    for sign in FORMATS:
        assert len(sign) == 1
