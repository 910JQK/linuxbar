#!/usr/bin/env python3


import sys
import threading
from time import sleep
from fetch import fetch_kw
from tieba_transport import move
from models import TiebaTopic
from config import (
    TIEBA_SYNC_ON, TIEBA_SYNC_KW, TIEBA_SYNC_INTERVAL, TIEBA_SYNC_DELAY,
    TIEBA_SYNC_PENDING_MAX, TIEBA_SYNC_OFFSET
)


waiting = 0


def sync():
    if not TIEBA_SYNC_ON:
        return
    # Update recent updated tieba topics,
    # which is necessary to avoid missing new replies
    recent_tieba_topics = (
        TiebaTopic
        .select()
        .order_by(TiebaTopic.last_update_date.desc())
        .paginate(1, TIEBA_SYNC_OFFSET)
    )
    kz_updated = {}
    for recent_topic in recent_tieba_topics:
        move(recent_topic.kz)
        kz_updated[recent_topic.kz] = True
    # Fetch new topics
    topics = fetch_kw(TIEBA_SYNC_KW, 1, 1)[:TIEBA_SYNC_OFFSET]
    topics.reverse()
    for topic in topics:
        if not topic['pin'] and not kz_updated.get(topic['kz']):
            move(topic['kz'])


def force_sync():
    global waiting
    if waiting <= TIEBA_SYNC_PENDING_MAX:
        waiting += 1


def start_sync():
    def sync_thread():
        global waiting
        while True:
            if waiting > 0:
                waiting -= 1
                sync()
                sleep(TIEBA_SYNC_DELAY)
            else:
                sleep(1)
    def timer_thread():
        global waiting
        while True:
            waiting += 1
            sleep(TIEBA_SYNC_INTERVAL)
    threading.Thread(target=sync_thread, args=()).start()
    threading.Thread(target=timer_thread, args=()).start()
