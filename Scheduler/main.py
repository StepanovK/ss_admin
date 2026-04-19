# main.py - добавить функцию init_token() и вызвать её при старте

import datetime
import random
import threading
import time

import schedule

from Models.AppTokens import AppToken
from Models.base import db
from Models.migration_manager import run_migrations
from config import debug
from config import logger, healthcheck_chat_id
from utils.Scripts import *
from utils.healthcheck import start_status_check
from utils.vk_oauth import VKOAuth

healthcheck_listener = None
healthcheck_poster = None


def init_token():
    """Инициализирует токен при старте шедулера"""
    logger.info("Initializing token from .env...")

    try:
        # Подключаемся к БД если нужно
        if db.is_closed():
            db.connect()

        # Запускаем миграции (создадут таблицу если нужно)
        run_migrations(db)

        # Принудительно обновляем токен из .env
        token_record = AppToken.force_update_from_env()

        if token_record:
            if token_record.is_expired(buffer_seconds=0):
                logger.warning(f"⚠️ Token is already expired! Expired at: {token_record.expires_at}")
                logger.warning("Please update ADMIN_ACCESS_TOKEN in .env file")
            else:
                expires_in = token_record.seconds_until_expiry()
                logger.info(f"✅ Token initialized successfully. Expires in {expires_in / 3600:.1f} hours")
        else:
            logger.warning("No token available. Admin API features may not work")

    except Exception as ex:
        logger.error(f"Failed to initialize token: {ex}")


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


def check_and_refresh_token():
    """Проверяет токен и обновляет его при необходимости"""
    logger.info('Проверка срока действия токена...')

    token_record = AppToken.get_master_token()

    if not token_record:
        logger.warning('Токен не найден в БД! Пытаемся загрузить из .env...')
        token_record = AppToken.force_update_from_env()

        if not token_record:
            send_token_expired_warning('Токен не найден в БД и в .env файле. Требуется ручная настройка.')
            return

    # Проверяем, не истёк ли токен
    if token_record.is_expired():
        logger.info(f'Токен истекает. Осталось {token_record.seconds_until_expiry():.0f} сек. Обновляем...')

        oauth = VKOAuth()

        if token_record.refresh_token:
            # Обновляем через refresh_token
            new_tokens = oauth.refresh_token(token_record.refresh_token)

            if new_tokens:
                AppToken.update_token(
                    access_token=new_tokens['access_token'],
                    refresh_token=new_tokens.get('refresh_token'),
                    expires_in=new_tokens.get('expires_in')
                )
                logger.info('Токен успешно обновлён через refresh_token')
            else:
                logger.error('Не удалось обновить токен через refresh_token')
                send_token_expired_warning('Не удалось обновить токен автоматически')
        else:
            logger.error('Нет refresh_token для обновления')
            send_token_expired_warning('Отсутствует refresh_token для обновления токена')
    else:
        logger.info(f'Токен актуален. Истекает через {token_record.seconds_until_expiry():.0f} сек.')


def send_token_expired_warning(message):
    """Отправляет предупреждение о проблемах с токеном в чат"""
    try:
        from utils.connection_holder import ConnectionsHolder
        vk = ConnectionsHolder().vk_connection_group

        vk.messages.send(
            peer_id=healthcheck_chat_id,
            message=f'⚠️ ПРОБЛЕМА С ТОКЕНОМ!\n\n{message}\n\n'
                    f'Требуется ручное обновление токена.\n'
                    f'Для обновления перейдите по ссылке:\n'
                    f'{VKOAuth().get_auth_url()}',
            random_id=random.randint(10 ** 5, 10 ** 6)
        )
    except Exception as ex:
        logger.error(f'Не удалось отправить предупреждение о токене: {ex}')


# Инициализируем токен при старте
init_token()

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
schedule.every(30).minutes.do(check_and_refresh_token)

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
