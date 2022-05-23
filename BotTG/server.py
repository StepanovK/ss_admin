import pathlib

import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import os
import config

from config import logger, config_db
from time import sleep
from tempfile import TemporaryDirectory
from pathlib import Path

from Models.Posts import Post, PostStatus

from threading import Thread
import schedule


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

        # TODO: переписать получение новых постов на kafka
        self.tmp_alarmed_posts = []

    def _connect_telegram(self):
        try:
            self.t_bot = telebot.TeleBot(self.tg_token, parse_mode='HTML')
        except Exception as err:
            logger.error(f'Не удалось подключиться к telegram по причине: {err}')

    def _clear_cache_dir(self):
        for data in self.cache_dir.iterdir():
            data.unlink()

    def _start_polling(self):
        logger.info(f'Обработка событий ТГ начата')

        for event in self.t_bot.get_updates():
            pass

    def _start_vk_event_detector(self):
        schedule.clear()
        schedule.every(10).seconds.do(self._check_new_vk_events)
        while True:
            try:
                schedule.run_pending()
            except Exception as err:
                logger.error(f'Не удалось выполнить получение новых событий из ВК по причине: {err}')

    def _check_new_vk_events(self):
        # TODO: переписать получение ID новых постов из сообщений kafka
        logger.info(f'Получение новостей. Получены посты: {self.tmp_alarmed_posts}')
        new_posts = Post.select().where(Post.suggest_status == PostStatus.SUGGESTED.value)

        for post in new_posts:
            if post.vk_id in self.tmp_alarmed_posts:
                continue

            logger.info(f'Сообщаем про пост: {post}')

            mes_text = f'Новый пост {post} от пользователя {post.user} в предложке!\n' \
                       f'Текст поста:\n' \
                       f'{post.text}'

            text_message = self.t_bot.send_message(
                chat_id=self.tg_chat_id,
                text=mes_text
            )

            self.tmp_alarmed_posts.append(post.vk_id)

        # self._clear_cache_dir()

    def run(self):
        polling = Thread(target=self._start_polling)
        updating = Thread(target=self._start_vk_event_detector)
        polling.start()
        updating.start()
        # try:
        #     polling.start()
        #     updating.start()
        # except Exception as ex:
        #     logger.error(ex)


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
                      tg_chat_id=config.telegram_chat_id, )
    server.run()
