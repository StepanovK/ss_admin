import datetime

import schedule
import time
from config import logger, debug
import threading

from utils.Scripts.ConversationsCleaning.cleaner import start_cleaning as conversation_cleaning
from utils.Scripts.ADS_Manager.ads_manager import check_ads_posts
from utils.Scripts.Dynamic_title_vk.dynamic_title_manager import update_title_vk
from utils.healthcheck import start_status_check

healthcheck = threading.Thread(target=start_status_check)
healthcheck.start()
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
    # time_to_send = datetime.datetime.now() + datetime.timedelta(minutes=1)
    # time_send_happy_birthday = f'{time_to_send:%H:%M}'

schedule.every(time_conversation_cleaning).minutes.do(conversation_cleaning)
schedule.every(time_check_ads_posts).minutes.do(check_ads_posts)
schedule.every(time_update_title_vk).minutes.do(update_title_vk)
# schedule.every().day.at(time_send_happy_birthday).do(send_happy_birthday)

logger.info(f'Starting...')
while True:
    try:
        schedule.run_pending()
    except Exception as ex:
        logger.error(f'Failed to run pending: {ex}')
    time.sleep(1)
