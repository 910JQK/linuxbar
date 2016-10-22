# Tieba Substitution (Still Under Development)

## Plan

A lightweight forum with the following features:

- support of several separate boards
- fudamental operations of topics and posts (e.g. add, edit...)
- nested posts (only 2 levels)
- auth and moderation system
- ban on specified user
- reply notification
- @ notification
- sticky topic
- classified distillate topic
- image uploading
- simple richtext support (e.g. bold, link, image...)
- code hightlighting
- full and robust API

## Principle

- keep it simple, stupid
- never take old browsers (such as IE) into consideration
- plain JS (no jQuery)
- no bitmap icons

## Testing

Dependencies: `python3` `peewee` `flask` `flask-babel`

As it is still under development, currently, we use Sqlite instead of MySQL for convenience.

Run it:
    $ python3 db.py # create database data.db (sqlite3)
    $ python3 app.py # run app, then goto http://localhost:5000

## TODO

- improve code and structure