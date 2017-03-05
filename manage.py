#!/usr/bin/env python3


import re
import os
import json
from getpass import getpass
from app import run
from models import User, Profile, init_db
from utils import now
from argparse import ArgumentParser


def create_administrator():
    mail = input('Email address: ')
    name = input('Nickname: ')
    password = getpass('Password: ')
    confirm = getpass('Confirm password: ')
    if password != confirm:
        print('Passwords are inconsistent.')
        return
    else:
        conflict = User.select().where(
            (User.mail == mail.lower())
            | (User.name == name)
        )
        if conflict:
            print('Conflict detected. Failed to create account.')
            return
        user = User(
            mail = mail.lower(),
            name = name,
            level = 2,
            date_register = now(),
            is_active = True
        )
        user.set_password(password)
        user.save(force_insert=True)
        Profile.create(user=user)
        print('New administrator created successfully.')


def create_post_move_account():
    name = input('Nickname: ')
    password = getpass('Password: ')
    confirm = getpass('Confirm password: ')
    if password != confirm:
        print('Passwords are inconsistent.')
        return
    else:
        user = User(
            mail = 'move_post@foobar',
            name = name,
            date_register = now(),
            is_active = True
        )
        user.set_password(password)
        user.save(force_insert=True)
        Profile.create(user=user)


def gen_js_trans_file():
    messages = {}
    TRANS_STR = re.compile('_\(\'([^\']+)')
    for filename in os.listdir('static'):
        if filename.endswith('.js'):
            path = os.path.join('static', filename)
            f = open(path)
            for line in f.readlines():
                for match in TRANS_STR.finditer(line):
                    msgid = match.expand('\\1')
                    messages[msgid] = ''
    msg_str = json.dumps(messages)
    msg_str = msg_str.replace('{', '{\n')
    msg_str = msg_str.replace(',', ',\n')
    msg_str = msg_str.replace('}', '\n}')
    print(msg_str)


def main():
    commands = {
        'run': run,
        'init-db': init_db,
        'create-admin': create_administrator,
        'create-move': create_post_move_account,
        'gen-js-trans': gen_js_trans_file
    }
    parser = ArgumentParser()
    parser.add_argument(
        'cmd',
        metavar='Command',
        help='(%s)' % '|'.join(list(commands))
    )
    args = parser.parse_args()
    if commands.get(args.cmd):
        commands[args.cmd]()
    else:
        print('Invalid command')


if __name__ == '__main__':
    main()
