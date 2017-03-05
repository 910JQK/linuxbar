import re
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound
from pygments.formatters import HtmlFormatter
from flask import url_for


from utils import _
from utils import *
from validation import REGEX_SHA256_PART, REGEX_PINT
from config import (
    LINK_PROTOCOLS,
    CODE_BEGIN,
    CODE_END,
    PID_SIGN,
    TID_SIGN,
    INLINE_CODE_SIGN,
    NOTIFICATION_SIGN,
    IMAGE_SIGN,
    FACE_SIGN,
    FORMAT_SIGN,
    FORMAT_DEFAULT,
    FORMATS,
    IMAGE_LIMIT,
    FACE_LIMIT,
    TIEBA_COMP,
    TIEBA_TIMG_URL,
    TIEBA_EMOTICON_URL
)


class Code():   
    text = ''
    lang = ''
    highlight = True
    def __init__(self, text, lang='text', highlight=True):
        self.text = text
        self.lang = lang
        self.highlight = highlight
    def __str__(self):
        if self.highlight:
            try:
                lexer = get_lexer_by_name(self.lang)
            except ClassNotFound:
                lexer = get_lexer_by_name('text')
            return highlight(self.text, lexer, HtmlFormatter())
        else:
            return (
                '%s %s\n%s\n%s' % (
                    CODE_BEGIN,
                    self.lang,
                    self.text, # no escape: storage stage
                    CODE_END
                )
            )


class FormattedText():
    text = ''
    def __init__(self, text):
        self.text = text
    def __str__(self):
        return self.text


def split_lines(text):
    return text.splitlines()


def process_code_block_raw(lines, highlight=False):
    in_code_block = False
    lang = ''
    code_lines = []
    for line in lines:
        if line.strip().endswith(CODE_END):
            code_lines.append(line[0:line.rfind(CODE_END)])
            yield Code('\n'.join(code_lines), lang, highlight=highlight)
            lang = ''
            code_lines = []
            in_code_block = False
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
    if in_code_block:
        yield Code('\n'.join(code_lines), lang, highlight=highlight)    


def process_code_block(lines):
    # tip: no escape !!!
    return process_code_block_raw(lines, highlight=False)


def process_code_block_with_highlight(lines):
    return process_code_block_raw(lines, highlight=True)


def process_line_without_format(line, process_segment):
    i = 0
    for snippet in line.split(INLINE_CODE_SIGN):
        if i % 2 == 1:
            yield INLINE_CODE_SIGN + snippet + INLINE_CODE_SIGN
        else:
            j = 0
            for sub_snippet in snippet.split(FORMAT_SIGN):
                if j % 2 == 1:
                    yield FORMAT_SIGN + sub_snippet + FORMAT_SIGN
                else:
                    yield ' '.join(
                        process_segment(seg) for seg in sub_snippet.split(' ')
                    )
                j += 1
        i += 1


def process_format(lines):
    count_image = 0
    count_face = 0
    def gen_html_tag(tag, content, **attrs):
        if not attrs:
            return '<%s>%s</%s>' % (tag, escape(content), tag)
        else:
            return '<%s %s>%s</%s>' % (
                tag,
                ' '.join(
                    '%s="%s"' % (key, value)
                    for key, value in attrs.items()
                ),
                escape(content),
                tag
            )
    def gen_image_html(url):
        return (
            '<a class="content_image_link" href="%s" target="_blank"><img class="content_image" src="%s" /></a>' % (url, url)
        )
    def gen_image_html_sha256(sha256part):
        url = url_for('image.get', sha256part=sha256part)
        return gen_image_html(url)
    def gen_face_html(face_name):
        url = url_for('image.face', name=face_name)
        return '<img class="content_image face" src="%s"></img>' % url
    def process_line_str(line):
        def process_formats(text):
            i = 0
            for snippet in text.split(FORMAT_SIGN):
                if i % 2 == 1 and snippet:
                    if FORMATS.get(snippet[0]):
                        yield FormattedText(
                            gen_html_tag(FORMATS[snippet[0]], snippet[1:])
                        )
                    else:
                        yield FormattedText(
                            gen_html_tag(FORMATS[FORMAT_DEFAULT], snippet)
                        )
                else:
                    # escape in next stage
                    yield snippet
                i += 1
        def process_segment(segment):
            nonlocal count_image
            nonlocal count_face
            # Tieba Compatibility
            if TIEBA_COMP:
                if segment.startswith(TIEBA_TIMG_URL):
                    return gen_image_html(segment)
                if re.match('\[[a-z_]+/[0-9a-z_\.\?=]+\]', segment):
                    return gen_image_html(
                        TIEBA_EMOTICON_URL + segment[1:-1]
                    )
            # ---------------------
            for protocol in LINK_PROTOCOLS:
                head = protocol + '://'
                if (
                        segment.startswith(head)
                        and len(segment) > len(head)
                ):
                    return gen_html_tag(
                        'a',
                        segment,
                        href = head + url_quote(segment[len(head):]),
                        target = '_blank'
                    )
            if segment.startswith(NOTIFICATION_SIGN*2):
                username = segment[2:]
                return gen_html_tag(
                    'a',
                    NOTIFICATION_SIGN + username,
                    href = url_for('user.profile_by_name', name=username),
                    target = '_blank'
                )
            if segment.startswith(IMAGE_SIGN) and count_image < IMAGE_LIMIT:
                sha256part = segment[len(IMAGE_SIGN):]
                if REGEX_SHA256_PART.fullmatch(sha256part):
                    count_image += 1
                    return gen_image_html_sha256(sha256part)
            if segment.startswith(FACE_SIGN) and count_face < FACE_LIMIT:
                face_name = segment[len(FACE_SIGN):]
                if not face_name.startswith(FACE_SIGN):
                    count_face += 1
                    return gen_face_html(face_name)
                else:
                    # preserve the original text
                    return face_name
            if segment.startswith(PID_SIGN):
                pid = segment[len(PID_SIGN):]
                if REGEX_PINT.fullmatch(pid):
                    pid = int(pid)
                    return gen_html_tag(
                        'a',
                        _('Post %d') % pid,
                        href = url_for('forum.post', pid=pid),
                        target = '_blank'
                    )
            if segment.startswith(TID_SIGN):
                tid = segment[len(TID_SIGN):]
                if REGEX_PINT.fullmatch(tid):
                    pid = int(pid)
                    return gen_html_tag(
                        'a',
                        _('Topic %d') % tid,
                        href = url_for('forum.topic_content', tid=tid),
                        target = '_blank'
                    )
            return escape(segment)
        def process():
            snippets = line.split(INLINE_CODE_SIGN)
            i = 0
            for snippet in snippets:
                if i % 2 == 1 and i != len(snippets)-1:
                    yield '<code>%s</code>' % escape(snippet)
                else:
                    if i % 2 == 1 and i == len(snippets)-1:
                        snippet = INLINE_CODE_SIGN + snippet
                    for sub_snippet in process_formats(snippet):
                        if not isinstance(sub_snippet, str):
                            yield str(sub_snippet)
                        else:
                            yield (
                                ' '.join(
                                    process_segment(seg)
                                    for seg in sub_snippet.split(' ')
                                )
                            )
                i += 1
        return ''.join(snippet for snippet in process())
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
    process_code_block_with_highlight,
    process_format,
    join_lines
)
