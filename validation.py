#!/usr/bin/env python3


HEXDIGITS = '0123456789abcdef'


class ValidationError(Exception):
    pass


def _(string):
    return string # reserved for l10n


def validate(field, string, min=0, max=0, not_empty=False):
    size = len(string.encode('utf8'))
    if(min and size < min):
        raise ValidationError(_(
            '%s should be at least %d bytes.' % (field, min)
        ))
    if(max and size > max):
        raise ValidationError(_(
            '%s should be at most %d bytes.' % (field, max)
        ))
    if(not_empty and size == 0):
        raise ValidationError(_('%s should not be empty.' % field))


def validate_sha256(field, string):
    if(len(string) != 64):
        raise ValidationError(_('%s should be a valid sha256 string.' % field))
    for char in string:
        if(char not in HEXDIGITS):
            raise ValidationError(_(
                '%s should be a valid sha256 string.' % field
            ))
