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
from Models.VK_Objects import User


class Server:
    vk_link = 'https://vk.com/'

    def __init__(self,
                 tg_token: str,
                 tg_chat_id: int,
                 vk_group_token: str,
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
        self.vk_api = None
        self.vk = None
        self._longpoll = None
        self._connect_vk()

        self.tg_token = tg_token
        self.tg_chat_id = tg_chat_id
        self.t_bot = None
        self._connect_telegram()

    def _connect_vk(self):
        try:
            self.vk_api = vk_api.VkApi(token=self.group_token)
            self.vk = self.vk_api.get_api()
        except Exception as err:
            logger.error(f'Не удалось подключиться к ВК по причине: {err}')

    def _connect_telegram(self):
        try:
            self.t_bot = telebot.TeleBot(self.tg_token, parse_mode='HTML')
        except Exception as err:
            logger.error(f'Не удалось подключиться к telegram по причине: {err}')

    def _clear_cache_dir(self):
        for data in self.cache_dir.iterdir():
            data.unlink()

    def _start_polling(self):
        if self.vk is None:
            self._connect_vk()
        self._longpoll = VkBotLongPoll(self.vk_api, self.group_id, )

        logger.info('Бот запущен')

        for event in self._longpoll.listen():

            if event.type == VkBotEventType.WALL_POST_NEW:
                pass

            self._clear_cache_dir()

    def run(self):
        try:
            self._start_polling()
        except Exception as ex:
            logger.error(ex)

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
                    vk_group_id=config.group_id)
    server.run_in_loop()
