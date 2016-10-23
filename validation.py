#!/usr/bin/env python3


import re


# Whether an email address is valid is finally checked by the activation mail
class regex():
    identifier = re.compile('[1-9][0-9]*')
    uint = re.compile('0|[1-9][0-9]*')
    email = re.compile('[^@]+@[^@]+')
    username = re.compile('[^<>"\'/\\\*@]{3,32}')
    token = re.compile('[0-9A-Za-z]{16}')
    sha256 = re.compile('[0123456789abcdef]{64}')
    board_short_name = re.compile('[0-9A-Za-z-]{1,32}')


class ValidationError(Exception):
    pass


def _(string):
    return string # reserved for l10n


def validate(field, string, min=0, max=0, not_empty=False, in_list=None, regex=None):
    if(not string):
        # may be None
        string = ''
    size = len(string.encode('utf8'))
    if(min and size < min):
        if(min == 1):
            raise ValidationError(_('%s should not be empty.') % field)
        else:
            raise ValidationError(
                _('%s should be at least %d bytes.') % (field, min)
            )
    if(max and size > max):
        raise ValidationError(
            _('%s should be at most %d bytes.') % (field, max)
        )
    if(not_empty and size == 0):
        raise ValidationError(_('%s should not be empty.') % field)
    if(in_list and string not in in_list):
        raise ValidationError(_('%s: Invalid value.') % field)
    if(regex and not regex.fullmatch(string)):
        if(size == 0):
            raise ValidationError(_('%s should not be empty.') % field)
        else:
            raise ValidationError(_('%s: Wrong format.') % field)


def validate_id(field, string):
    validate(field, string, regex=id_regex)


def validate_uint(field, string):
    validate(field, string, regex=uint_regex)


def validate_email(field, string):
    validate(field, string, min=3, max=64, regex=email_regex)


def validate_username(field, string):
    validate(field, string, regex=username_regex)


def validate_token(field, string):
    validate(field, string, regex=token_regex)


def validate_sha256(field, string):
    validate(field, string, regex=sha256_regex)


def validate_board(field, string):
    validate(field, string, regex=board_short_name_regex)
