import datetime

import schedule
import time
from config import logger, debug
import threading

from utils.Scripts import *
from utils.healthcheck import start_status_check

healthcheck_listener = None
healthcheck_poster = None


def start_healthcheck():
    start_healthcheck_listener()
    start_healthcheck_poster()


def start_healthcheck_listener():
    global healthcheck_listener
    healthcheck_listener = threading.Thread(target=start_status_check, args=('listener',))
    healthcheck_listener.start()


def start_healthcheck_poster():
    global healthcheck_poster
    healthcheck_poster = threading.Thread(target=start_status_check, args=('poster',))
    healthcheck_poster.start()


start_healthcheck()

if debug:
    time_conversation_cleaning = 1
    time_check_ads_posts = 1
    time_update_title_vk = 1
    time_to_send = datetime.datetime.now() + datetime.timedelta(minutes=1)
    time_send_happy_birthday = f'{time_to_send:%H:%M}'
else:
    time_conversation_cleaning = 30
    time_check_ads_posts = 10
    time_update_title_vk = 10
    time_send_happy_birthday = "09:00"

schedule.every(time_conversation_cleaning).minutes.do(conversation_cleaning)
schedule.every(time_check_ads_posts).minutes.do(check_ads_posts)
schedule.every(time_update_title_vk).minutes.do(update_title_vk)
schedule.every().day.at(time_send_happy_birthday).do(send_happy_birthday)

logger.info(f'Starting...')
while True:
    try:
        schedule.run_pending()
    except Exception as ex:
        logger.error(f'Failed to run pending: {ex}')

    time.sleep(1)

    if healthcheck_listener is None or (
            isinstance(healthcheck_listener, threading.Thread) and not healthcheck_listener.is_alive()):
        logger.warning(f'healthcheck_listener упал! Перезапускаем!')
        start_healthcheck_listener()

    if healthcheck_poster is None or (
            isinstance(healthcheck_poster, threading.Thread) and not healthcheck_poster.is_alive()):
        logger.warning(f'healthcheck_poster упал! Перезапускаем!')
        start_healthcheck_poster()
