from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound
from pygments.formatters import HtmlFormatter
from flask import url_for


from utils import *
from config import (
    CODE_BEGIN, CODE_END, INLINE_CODE_SIGN, NOTIFICATION_SIGN, FORMATS
)


class Code():    
    text = ''
    lang = ''
    def __init__(self, text, lang='text'):
        self.text = text
        self.lang = lang
    def __str__(self):
        try:
            lexer = get_lexer_by_name(self.lang)
        except ClassNotFound:
            lexer = get_lexer_by_name('text')
        return highlight(self.text, lexer, HtmlFormatter())


def split_lines(text):
    return text.splitlines()


def process_code_block(lines):
    in_code_block = False
    lang = ''
    code_lines = []
    for line in lines:
        if line.strip().endswith(CODE_END):
            yield Code('\n'.join(code_lines), lang)
            lang = ''
            code_lines = []
            code_block_count = False
        elif in_code_block:
            code_lines.append(line)
        elif line.strip().startswith(CODE_BEGIN):
            segments = line.split()
            if len(segments) > 1:
                lang = segments[1]
            else:
                lang = 'text'
            in_code_block = True
        else:
            yield line


def process_format(lines):
    def gen_html_tag(tag, content, **attrs):
        if not attrs:
            return '<%s>%s</%s>' % (tag, escape(content), tag)
        else:
            return '<%s %s>%s</%s>' % (
                tag,
                escape(content),
                ' '.join(
                    '%s="%s"' % (key, value)
                    for key, value in attr.items()
                ),
                tag
            )
    def gen_image_html(sha256):
        url = url_for('image.get', sha256=sha256)
        return (
            '<a class="content_image_link" href="%s" target="_blank"><img class="content_image" src="%s"></img></a>' % (url, url)
        )
    def process_line_str(line):
        def process_segment(segment):
            if segment.startswith(NOTIFICATION_SIGN*2):
                username = segment[2:]
                return gen_html_tag(
                    'a',
                    username,
                    href = url_for('user.profile_by_name', name=username),
                    target = '_blank'
                )
            if segment.startswith(IMAGE_SIGN*2):
                sha256 = segment[2:]
                return gen_image_html(sha256)
            if (
                    segment.startswith(INLINE_CODE_SIGN)
                    and segment.endswith(INLINE_CODE_SIGN)
            ):
                return gen_html_tag('code', segment[1:-1])
            for char in FORMATS:
                if segment.startswith(char*2):
                    return gen_html_tag(FORMATS[char], segment[2:])
            return escape(segment)
        for char in FORMATS:
            if line.startswith(char*3):
                return gen_html_tag(FORMATS[char], line[3:])
        return ' '.join(process_segment(seg) for seg in line.split())
    for line in lines:
        if isinstance(line, str):
            yield process_line_str(line)
        else:
            yield str(line)


def join_lines(lines):
    return '\n'.join(lines)


def pipeline(*processors):
    def process(text):
        for proc in processors:
            text = proc(text)
        return text
    return process


get_content_html = pipeline(
    split_lines,
    process_code_block,
    process_format,
    join_lines
)
