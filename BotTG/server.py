import pathlib

import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import os
import config

from config import logger, config_db
from time import sleep
from tempfile import TemporaryDirectory
from pathlib import Path


class TgServer:
    def __init__(self,
                 tg_token: str,
                 tg_chat_id: int,
                 cache_dir: str = None
                 ):
        self.cache_dir = cache_dir if cache_dir else get_cache_dir()
        try:
            os.chdir(self.cache_dir)
        except FileNotFoundError:
            self.cache_dir.mkdir()

        self.tg_token = tg_token
        self.tg_chat_id = tg_chat_id
        self.t_bot = None
        self._connect_telegram()

    def _connect_telegram(self):
        try:
            self.t_bot = telebot.TeleBot(self.tg_token, parse_mode='HTML')
        except Exception as err:
            logger.error(f'Не удалось подключиться к telegram по причине: {err}')

    def _clear_cache_dir(self):
        for data in self.cache_dir.iterdir():
            data.unlink()

    def _start_polling(self):
        for event in self.t_bot.get_updates():
            pass

            # self._clear_cache_dir()

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
    server = TgServer(tg_token=config.telegram_bot_token,
                    tg_chat_id=config.telegram_chat_id,)
    server.run_in_loop()
