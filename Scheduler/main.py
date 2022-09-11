import schedule
import time
from config import logger

from utils.Scripts.ConversationsCleaning.cleaner import start_cleaning as conversation_cleaning
from utils.Scripts.ADS_Manager.ads_manager import check_ads_posts

schedule.every(30).minutes.do(conversation_cleaning)
schedule.every(10).minutes.do(check_ads_posts)

while True:
    try:
        schedule.run_pending()
    except Exception as ex:
        logger.error(f'Failed to run pending: {ex}')
    time.sleep(1)
