#!/usr/bin/env python3


from getpass import getpass
from app import run
from models import User, init_db
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
        user = User(
            mail = mail,
            name = name,
            admin_level = 2,
            date_register = now(),
            is_active = True
        )
        user.set_password(password)
        user.save(force_insert=True)
        print('New administrator created successfully.')


def main():
    commands = {
        'run': run,
        'init-db': init_db,
        'create-admin': create_administrator
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
