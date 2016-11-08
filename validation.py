#!/usr/bin/env python3


import re
from wtforms.validators import ValidationError
from utils import _


REGEX_USERNAME = re.compile('[^<>"\'/\\\*@]{3,32}')
REGEX_SHA256 = re.compile('[0123456789abcdef]{64}')
REGEX_BOARD_SLUG = re.compile('[0-9A-Za-z-]{1,32}')
REGEX_TOKEN = re.compile('[0-9A-Za-z]{16}')


def size_validator(min=0, max=0):
    def check(field):
        label = field.label
        string = field.data
        size = len(string.encode('utf8'))
        if(min and size < min):
            raise ValidationError(
                _('%s should be at least %d bytes.') % (label, min)
            )
        if(max and size > max):
            raise ValidationError(
                _('%s should be at most %d bytes.') % (label, max)
            )
    return check
