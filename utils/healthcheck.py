import datetime
import random
import time
import threading
from utils.rabbit_connector import send_message, get_messages

import config
from utils.connection_holder import ConnectionsHolder
from config import logger


def start_status_check(service_name: str):
    vk_connection_group = ConnectionsHolder().vk_connection_group

    logger.info(f'Status checking of {service_name} started!')

    message_type_requests = f'{config.healthcheck_queue_name_prefix}_{service_name}_requests'
    message_type_answers = f'{config.healthcheck_queue_name_prefix}_{service_name}_answers'

    while True:
        start_time = datetime.datetime.now()
        stop_time = start_time + datetime.timedelta(seconds=config.healthcheck_timeout)
        message_text = f'healthcheck {start_time:%Y.%m.%d %H:%M:%S}'
        send_message(message_type=message_type_requests, message=message_text)

        while True:
            messages = get_messages(message_type=message_type_answers)

            if message_text in messages:
                break
            elif datetime.datetime.now() < stop_time:
                time.sleep(1)
            else:
                text_message = f'ВНИМАНИЕ! {service_name} не работает!!! ({datetime.datetime.now().strftime("%H:%M:%S")})'
                logger.warning(text_message)
                try:
                    vk_connection_group.messages.send(peer_id=config.healthcheck_chat_id,
                                                      message=text_message,
                                                      random_id=random.randint(10 ** 5, 10 ** 6))
                except Exception as ex:
                    logger.warning(f'Failed send message peer_id={config.healthcheck_chat_id}\n{ex}')
                break


if __name__ == '__main__':
    start_status_check()
