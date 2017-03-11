#!/usr/bin/env python3


import sys
import time
from fetch import fetch_kw
from tieba_transport import move


DELAY = 30
OFFSET = 10


def sync(kw):
    while True:
        topics = fetch_kw(kw, 1, 1)[:OFFSET]
        topics.reverse()
        for topic in topics:
            if not topic['pin']:
                move(topic['kz'])
        time.sleep(DELAY)


if __name__ == '__main__':
    sync(sys.argv[1])
