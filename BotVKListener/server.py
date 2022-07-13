from typing import Dict

import config as config
from config import logger
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from time import sleep
import datetime
import pika
from Models.base import db
from Models.Posts import Post, PostStatus
from Models.PrivateMessages import PrivateMessage
from Models import create_db
from utils.db_helper import queri_to_list
from utils.connection_holder import ConnectionsHolder
from ChatBot.chat_bot import ChatBot
from Parser import comments, likes, posts, subscriptions, private_messages, conversations, _initial_downloading


class Server:
    vk_link = 'https://vk.com/'

    def __init__(self):
        self.group_id = config.group_id
        self.chat_bot = ChatBot()

        self.queue_name_prefix = config.queue_name_prefix

        self.chat_for_suggest = config.chat_for_suggest

        self.vk_api_admin = ConnectionsHolder().vk_api_admin
        self.vk_connection_admin = ConnectionsHolder().vk_connection_admin
        self.vk_api_group = ConnectionsHolder().vk_api_group
        self.vk_connection_group = ConnectionsHolder().vk_connection_group

    def _start_polling(self):
        self._longpoll = VkBotLongPoll(self.vk_api_group, self.group_id, wait=5)

        logger.info('Bot listener started!')

        time_to_update_last_posts = 10
        last_published_posts_update = None

        while True:
            for event in self._longpoll.check():

                logger.info(f'New event: {event.type}')
                if event.type == VkBotEventType.WALL_POST_NEW:
                    new_post = posts.parse_wall_post(event.object, self.vk_connection_admin)
                    str_from_user = '' if new_post.user is None else f'от {new_post.user} '
                    str_attachments = '' if len(
                        new_post.attachments) == 0 else f', вложений: {len(new_post.attachments)}'
                    str_action = 'Post published' if new_post.suggest_status is None else 'Suggested new post'
                    logger.info(f'{str_action} {str_from_user}{new_post}{str_attachments}')
                    if self.queue_name_prefix != '' and new_post.suggest_status == PostStatus.SUGGESTED.value:
                        self._send_alarm(message_type='new_suggested_post', message=new_post.id)
                    elif self.queue_name_prefix != '' and new_post.suggest_status is None:
                        self._send_alarm(message_type='new_posted_post', message=new_post.id)
                elif event.type == 'like_add':
                    likes.parse_like_add(event.object, self.vk_connection_admin)
                elif event.type == 'like_remove':
                    likes.parse_like_remove(event.object, self.vk_connection_admin)
                elif event.type == VkBotEventType.WALL_REPLY_NEW:
                    comments.parse_comment(event.object, self.vk_connection_admin)
                elif event.type == VkBotEventType.WALL_REPLY_DELETE:
                    comments.parse_delete_comment(event.object, self.vk_connection_admin)
                elif event.type == VkBotEventType.WALL_REPLY_RESTORE:
                    comments.parse_restore_comment(event.object, self.vk_connection_admin)
                elif event.type == VkBotEventType.GROUP_JOIN:
                    subscriptions.parse_subscription(event, self.vk_connection_admin, True)
                elif event.type == VkBotEventType.GROUP_LEAVE:
                    subscriptions.parse_subscription(event, self.vk_connection_admin, False)
                elif event.type == VkBotEventType.BOARD_POST_NEW:
                    conversations.parse_conversation_message(event.object, self.vk_connection_admin)
                elif event.type == VkBotEventType.BOARD_POST_EDIT:
                    conversations.parse_conversation_message(event.object, self.vk_connection_admin, is_edited=True)
                elif event.type == VkBotEventType.BOARD_POST_EDIT:
                    conversations.parse_delete_conversation_message(event.object)
                elif event.type == VkBotEventType.MESSAGE_NEW:
                    if event.from_chat and str(event.object['message']['peer_id']) == str(self.chat_for_suggest):
                        if 'load_data' in event.object.message['text']:
                            words = event.object.message['text'].split()
                            if len(words) == 1:
                                _initial_downloading.load_all(self.vk_connection_admin)
                            elif len(words) == 2 and words[1].isdigit():
                                group_id = int(event.object.message['text'].split()[1])
                                _initial_downloading.load_all(self.vk_connection_admin, group_id)
                        if event.object.message['text'] == 'create_db':
                            db.close()
                            sleep(1)
                            create_db.create_all_tables()
                        elif event.object.message['text'] == 'recreate_db':
                            db.close()
                            sleep(1)
                            create_db.recreate_database()
                        elif event.object.message['text'] == 'lock_db':
                            create_db.lock_db()
                        elif event.object.message['text'] == 'unlock_db':
                            create_db.unlock_db()
                    else:
                        if PrivateMessage.it_is_private_chat(event.object.message.get('peer_id')):
                            message = private_messages.parse_private_message(event.object.message,
                                                                             self.vk_connection_admin)
                            self._send_alarm(message_type='new_private_message', message=message.id)
                        self.chat_bot.chat(event)

                elif event.type == VkBotEventType.MESSAGE_REPLY:
                    if PrivateMessage.it_is_private_chat(event.object.get('peer_id')):
                        if event.from_user:
                            message = private_messages.parse_private_message(event.object,
                                                                             self.vk_connection_admin)
                            self._send_alarm(message_type='new_private_message', message=message.id)

            now = datetime.datetime.now()
            if not last_published_posts_update \
                    or (now - last_published_posts_update).total_seconds() >= time_to_update_last_posts:
                try:
                    self._update_last_posts()
                except Exception as ex:
                    logger.error(f'Failed to update last posts: {ex}')
                last_published_posts_update = datetime.datetime.now()

    def _update_last_posts(self, count_of_posts: int = 60):
        days_for_update = 3

        date_to_start = datetime.datetime.now() - datetime.timedelta(days=days_for_update)
        last_posts = Post.select().where((Post.date > date_to_start)
                                         & ((Post.suggest_status.is_null())
                                            | (Post.suggest_status != PostStatus.REJECTED.value))
                                         & (Post.is_deleted == False)
                                         ).order_by(Post.date.desc()).limit(count_of_posts)
        last_posts_list = queri_to_list(last_posts, 'id')
        if len(last_posts_list) > 0:
            # print(f'updating posts: {last_posts_list}')
            posts_info = self.vk_connection_admin.wall.getById(posts=', '.join(last_posts_list))
            for post_info in posts_info:
                post, was_updated = posts.update_wall_post(post_info, self.vk_connection_admin)
                if was_updated:
                    self._send_alarm('updated_posts', post.id)
                # print(f'post {post} was_updated={was_updated}')

    def _send_alarm(self, message_type: str, message: str):
        channel = ConnectionsHolder().rabbit_connection.channel()
        queue_name = f'{self.queue_name_prefix}_{message_type}'
        channel.queue_declare(queue=queue_name,
                              durable=True)
        channel.basic_publish(exchange='',
                              routing_key=queue_name,
                              body=message.encode(),
                              properties=pika.BasicProperties(delivery_mode=2))

        ConnectionsHolder().close_rabbit_connection()

    def run(self):
        # try:
        self._start_polling()
        # except Exception as ex:
        #     logger.error(ex)

    def run_in_loop(self):
        while True:
            self.run()
            sleep(10)


if __name__ == '__main__':
    server = Server()
    server.run_in_loop()
