# Tieba Substitute (Still Under Development)

## Plan

A lightweight forum with the following features:

- support of tags
- fudamental operations of topics and posts (e.g. add, edit...)
- unlimited nested posts
- auth and moderation system
- ban on specified user
- reply notification
- @ notification
- sticky topic
- distillate topic
- image uploading
- simple richtext support (e.g. bold, link, image...)
- code hightlighting
- full and robust API

## Principle

- keep it simple, stupid
- never take old browsers (such as IE) into consideration
- plain JS (no jQuery)
- work well without JavaScript
- no bitmap icons

## Testing

As it is still under development, currently, we use Sqlite instead of MySQL for convenience.

Run it:
    
    $ pip install -r requirements.txt # install dependencies
    $ ./manage.py init-db # create database data.db (sqlite3)
    $ ./manage.py create-admin # create an administrator account
    $ ./manage.py run # run app, then goto http://localhost:5000

