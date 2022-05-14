import pathlib

import telebot
import os
import config

from vk_api import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from config import logger, config_db
from time import sleep
from tempfile import TemporaryDirectory
from pathlib import Path
import vk_obj_parser


class Server:
    vk_link = 'https://vk.com/'

    def __init__(self,
                 tg_token: str,
                 tg_chat_id: int,
                 vk_group_token: str,
                 admin_token: str,
                 admin_phone: str,
                 admin_pass: str,
                 vk_group_id: int,
                 cache_dir: str = None
                 ):
        self.cache_dir = cache_dir if cache_dir else get_cache_dir()
        try:
            os.chdir(self.cache_dir)
        except FileNotFoundError:
            self.cache_dir.mkdir()

        self.group_token = vk_group_token
        self.group_id = vk_group_id
        self.admin_token = admin_token
        self.admin_phone = admin_phone
        self.admin_pass = admin_pass
        self.vk_api = None
        self.vk_connection = None
        self.vk_api_admin = None
        self.vk_connection_admin = None
        self._longpoll = None
        self._connect_vk()
        self._connect_vk_admin()

        self.tg_token = tg_token
        self.tg_chat_id = tg_chat_id
        self.t_bot = None
        self._connect_telegram()

    def _connect_vk(self):
        try:
            self.vk_api = vk_api.VkApi(token=self.group_token)
            self.vk_connection = self.vk_api.get_api()
        except Exception as err:
            logger.error(f'Не удалось подключиться к ВК по причине: {err}')

    def _connect_vk_admin(self):
        try:
            self.vk_api_admin = vk_api.VkApi(
                login=self.admin_phone,
                password=self.admin_pass,
                token=self.admin_token)
            self.vk_connection_admin = self.vk_api_admin.get_api()
        except Exception as err:
            logger.error(f'Не удалось подключиться к ВК под админом по причине: {err}')

    def _connect_telegram(self):
        try:
            self.t_bot = telebot.TeleBot(self.tg_token, parse_mode='HTML')
        except Exception as err:
            logger.error(f'Не удалось подключиться к telegram по причине: {err}')

    def _clear_cache_dir(self):
        for data in self.cache_dir.iterdir():
            data.unlink()

    def _start_polling(self):
        if self.vk_connection is None:
            self._connect_vk()
        self._longpoll = VkBotLongPoll(self.vk_api, self.group_id, )

        logger.info('Бот запущен')

        for event in self._longpoll.listen():

            logger.info(f'Новое событие {event.type}')
            if event.type == VkBotEventType.WALL_POST_NEW:
                new_post = vk_obj_parser.parse_wall_post(event.object, self.vk_connection_admin)
                str_from_user = '' if new_post.user is None else f'от {new_post.user} '
                str_attachments = '' if len(new_post.attachments) == 0 else f', вложений: {len(new_post.attachments)}'
                str_action = 'Опубликован пост' if new_post.suggest_status is None else 'В предложке новый пост'
                logger.info(f'{str_action} {str_from_user}{new_post}{str_attachments}')
            elif event.type == 'like_add':
                vk_obj_parser.parse_like_add(event.object, self.vk_connection_admin)
            elif event.type == 'like_remove':
                vk_obj_parser.parse_like_remove(event.object, self.vk_connection_admin)
            elif event.type == VkBotEventType.WALL_REPLY_NEW:
                vk_obj_parser.parse_comment(event.object, self.vk_connection_admin)
            # self._clear_cache_dir()

    def run(self):
        # try:
        self._start_polling()
        # except Exception as ex:
        #     logger.error(ex)

    def run_in_loop(self):
        while True:
            self.run()
            sleep(60)


def get_cache_dir() -> pathlib.Path:
    if os.name != "nt":
        tmp_dir = TemporaryDirectory()
        cache_dir = Path(tmp_dir.name)
    else:
        cache_dir = Path.cwd() / ".cache"
    cache_dir = Path(cache_dir).absolute()

    return cache_dir


if __name__ == '__main__':
    server = Server(tg_token=config.telegram_bot_token,
                    tg_chat_id=config.telegram_chat_id,
                    vk_group_token=config.group_token,
                    admin_token=config.admin_token,
                    admin_phone=config.admin_phone,
                    admin_pass=config.admin_pass,
                    vk_group_id=config.group_id)
    server.run_in_loop()
