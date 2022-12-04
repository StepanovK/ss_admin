import schedule
import time
from config import logger, debug

from utils.Scripts.ConversationsCleaning.cleaner import start_cleaning as conversation_cleaning
from utils.Scripts.ADS_Manager.ads_manager import check_ads_posts
from utils.Scripts.Dynamic_title_vk.dynamic_title_manager import update_title_vk

if debug:
    time_conversation_cleaning = 1
    time_check_ads_posts = 1
    time_update_title_vk = 1
else:
    time_conversation_cleaning = 30
    time_check_ads_posts = 10
    time_update_title_vk = 10

schedule.every(time_conversation_cleaning).minutes.do(conversation_cleaning)
schedule.every(time_check_ads_posts).minutes.do(check_ads_posts)
schedule.every(time_update_title_vk).minutes.do(update_title_vk)

logger.error(f'Starting...')
while True:
    try:
        schedule.run_pending()
    except Exception as ex:
        logger.error(f'Failed to run pending: {ex}')
    time.sleep(1)
