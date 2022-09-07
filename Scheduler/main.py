import schedule
import time
from config import logger

from utils.ConversationsCleaning.cleaner import start_cleaning as conversation_cleaning

schedule.every(30).minute.do(conversation_cleaning)

while True:
    try:
        schedule.run_pending()
    except Exception as ex:
        logger.error(f'Failed to run pending: {ex}')
    time.sleep(1)
