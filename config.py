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


DEBUG = True
SECRET_KEY = b'\xe9\xd3\x8fV0n\xcajX~P%*\xf1=O\xb7\xbc\xfa\xe5\xf5db'
TOKEN_LIFETIME = 20 # minutes
SUMMARY_LENGTH = 60 # in [4, 128] (128 = Topic.summary.max_length / 4)
BAN_DAYS = [1, 3, 10, 30, 100]


LINK_PROTOCOLS = ['http', 'https', 'ftp']
CODE_BEGIN = '/***#'
CODE_END = '#***/'
PID_SIGN = 'p#'
TID_SIGN = 't#'
INLINE_CODE_SIGN = '`' # a single char
NOTIFICATION_SIGN = '@' # a single char
IMAGE_SIGN = '%' # a single char
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
  "code_prefix": "/***#",
  "code_suffix": "#***/"
}
'''


UPLOAD_FOLDER = 'upload'
MAX_UPLOAD_SIZE = 5 * 1024 * 1024
IMAGE_MIME = {'png': 'image/png', 'jpeg': 'image/jpeg', 'gif': 'image/gif'}


def assert_config():
    assert os.path.isdir(UPLOAD_FOLDER)
    assert SUMMARY_LENGTH in range(4, 128+1)
    assert len(INLINE_CODE_SIGN) == 1
    assert len(NOTIFICATION_SIGN) == 1
    assert len(IMAGE_SIGN) == 1
    assert len(FORMAT_DEFAULT) == 1
    for sign in FORMATS:
        assert len(sign) == 1    
