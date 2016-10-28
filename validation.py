#!/usr/bin/env python3


import re
from utils import _


# Whether an email address is valid is finally checked by the activation mail
class regex():
    id = re.compile('[1-9][0-9]*')
    uint = re.compile('0|[1-9][0-9]*')
    email = re.compile('[^@]+@[^@]+')
    username = re.compile('[^<>"\'/\\\*@]{3,32}')
    login = re.compile('[^<>"\'/\\\*]{3, 64}')
    token = re.compile('[0-9A-Za-z]{16}')
    sha256 = re.compile('[0123456789abcdef]{64}')
    board = re.compile('[0-9A-Za-z-]{1,32}')
    config = re.compile('[0-9A-Za-z_]{1,32}')


def create_validator(name, min=0, max=0, required=False, in_list=None, regex=None):
    def check(string):
        def invalid(msg):
            return (False, msg)
        if(not string):
            # may be None
            string = ''
        size = len(string.encode('utf8'))
        if(min and size < min):
            if(min == 1):
                return invalid(_('%s should not be empty.') % name)
            else:
                return invalid(
                    _('%s should be at least %d bytes.') % (name, min)
                )
        if(max and size > max):
            return invalid(
                _('%s should be at most %d bytes.') % (name, max)
            )
        if(required and size == 0):
            return invalid(_('%s should not be empty.') % name)
        if(in_list and string not in in_list):
            return invalid(_('%s: Invalid value.') % name)
        if(regex and not regex.fullmatch(string)):
            if(size == 0):
                return invalid(_('%s should not be empty.') % name)
            else:
                return invalid(_('%s: Wrong format.') % name)
        return (True, None)
    check.field_name = name
    check.requirements = kwargs
    return check


def optional(validator):
    def new_validator(string):
        if not string:
            return (True, None)
        else:
            return validator(string)
    return new_validator


class validator():
    create = create_validator
    @staticmethod
    def id(name=_('ID')):
        return create_validator(name, regex=regex.id)
    @staticmethod
    def level(name=_('Level')):
        return create_validator(name, regex=regex.uint)
    @staticmethod
    def count(name=_('Count per Page')):
        return create_validator(name, regex=regex.id)
    @staticmethod
    def email(name=_('Email Address')):
        return create_validator(name, min=3, max=64, regex=regex.email)
    @staticmethod
    def username(name=_('Username')):
        return create_validator(name, regex=regex.username)
    @staticmethod
    def login(name=_('Login Name')):
        return create_validator(name, regex=regex.login)
    @staticmethod
    def password(name=_('Password')):
        return create_validator(name, min=1, max=64)
    @staticmethod
    def token(name=_('Token')):
        return create_validator(name, regex=regex.token)
    @staticmethod
    def sha256(name=_('SHA-256')):
        return create_validator(name, regex=regex.sha256)
    @staticmethod
    def board(name=_('Board Slug')):
        return create_validator(name, regex=regex.board)
    @staticmethod
    def config(name=_('Config Item Name')):
        return create_validator(name, regex=regex.config)
