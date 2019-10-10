# Tieba Substitute (Still Under Development)

> **NOTE**: 此项目的开发已经终止。但由于*度贴吧隐藏了 2017 年以前的所有帖子，此项目的遗留程序已被用于将 Linux 吧所有旧精品帖备份在 [linuxbar.pythonanywhere.com](http://linuxbar.pythonanywhere.com/)

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
- full and robust API  // not implemented

## Principle

- keep it simple, stupid
- never take old browsers (such as IE) into consideration
- plain JS (no jQuery)
- work well without JavaScript
- no bitmap icons

## Testing

> As it is still under development, currently, we use Sqlite instead of MySQL for convenience.

### Run it
    
    $ pip install -r requirements.txt # install dependencies
    $ pybabel compile -d translations # generate mo files
    $ cp config.example.py config.py # create configuration file
    $ "$EDITOR" config.py # edit configurations
    $ ./manage.py init-db # create database data.db (sqlite3)
    $ ./manage.py create-admin # create an administrator account
    $ ./manage.py run # run app, then goto http://localhost:5000

### Sync with Tieba

Firstly, put `fetch.py` of [tieba-fetch](https://github.com/910JQK/tieba-fetch) in this directory.

And create an account as the author of moved posts:

    $ ./manage.py create-move
    
Opening the compatible option `TIEBA_COMP` is also necessary:

    $ "$EDITOR" config.py

Then you can transport specified topics from Tieba:

    $ ./tieba_transport.py 4834742871 4809205799 # for example

Furthermore, it is possible to open the `TIEBA_SYNC_ON` option to enable the sync with tieba. Don't forget to set the `TIEBA_SYNC_KW` option to the bar you want to sync with.

Any user can go to `http://[site]/tieba/sync/settings` to bind his or her Tieba account with the corresponding account of this site.

Finally, please note that this feature is unstable.