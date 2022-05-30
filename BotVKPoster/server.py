import utils.config as config
from utils.config import logger
from vk_api import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from time import sleep
from BotVKPoster.PosterModels.MessagesOfSuggestedPosts import MessageOfSuggestedPost
from BotVKPoster.PosterModels import create_db
from utils.connection_holder import VKConnectionsHolder
import pika
import datetime
import json
import random
from Models.Posts import Post
from Models.Relations import PostsAttachment, PostsLike


class Server:
    vk_link = 'https://vk.com/'

    def __init__(self):
        self.group_id = config.group_id

        self.rabbitmq_host = config.rabbitmq_host
        self.rabbitmq_port = config.rabbitmq_port
        self.queue_name_prefix = config.queue_name_prefix

        self.chat_for_suggest = config.chat_for_suggest

        self.vk_api_admin = VKConnectionsHolder().vk_api_admin
        self.vk_admin = VKConnectionsHolder().vk_connection_admin
        self.vk_api_group = VKConnectionsHolder().vk_api_group
        self.vk = VKConnectionsHolder().vk_connection_group

    def _start_polling(self):

        self._longpoll = VkBotLongPoll(self.vk_api_group, self.group_id, wait=5)

        time_to_update_broker = 10
        last_broker_update = None

        # События очереди из брокера проверяются после ожидания событий от ВК, но не чаще time_to_update_broker
        # Время ожидания событий от вк задаётся параметром wait класса VkBotLongPoll
        while True:
            logger.info('Проверка событий ВК')
            for event in self._longpoll.check():
                logger.info(f'обработка события ВК {event.type}')
                if event.type == VkBotEventType.MESSAGE_NEW:
                    if event.from_chat:
                        if str(event.object['message']['peer_id']) == str(self.chat_for_suggest):
                            if event.object['message']['text'] == 'create_db':
                                create_db.create_all_tables()

            now = datetime.datetime.now()
            if not last_broker_update or (now - last_broker_update).total_seconds() >= time_to_update_broker:
                logger.info('Проверка событий очереди')
                self.start_consuming()
                last_broker_update = datetime.datetime.now()

        #
        # logger.info('Бот запущен')
        #
        # for event in self._longpoll.listen():
        #     logger.info(f'Новое событие {event.type}')
        #     if event.type == VkBotEventType.MESSAGE_NEW:
        #         if event.from_chat:
        #             if str(event.object['message']['peer_id']) == str(self.chat_for_suggest):
        #                 if event.object['message']['text'] == 'create_db':
        #                     create_db.create_all_tables()

        # if event.type == VkBotEventType.WALL_POST_NEW:
        #     new_post = posts.parse_wall_post(event.object, self.vk_connection_admin)
        #     str_from_user = '' if new_post.user is None else f'от {new_post.user} '
        #     str_attachments = '' if len(new_post.attachments) == 0 else f', вложений: {len(new_post.attachments)}'
        #     str_action = 'Опубликован пост' if new_post.suggest_status is None else 'В предложке новый пост'
        #     logger.info(f'{str_action} {str_from_user}{new_post}{str_attachments}')
        # elif event.type == 'like_add':
        #     likes.parse_like_add(event.object, self.vk_connection_admin)
        # elif event.type == 'like_remove':
        #     likes.parse_like_remove(event.object, self.vk_connection_admin)
        # elif event.type == VkBotEventType.WALL_REPLY_NEW:
        #     comments.parse_comment(event.object, self.vk_connection_admin)
        # elif event.type == VkBotEventType.WALL_REPLY_DELETE:
        #     comments.parse_delete_comment(event.object, self.vk_connection_admin)
        # elif event.type == VkBotEventType.WALL_REPLY_RESTORE:
        #     comments.parse_restore_comment(event.object, self.vk_connection_admin)
        # elif event.type == VkBotEventType.GROUP_JOIN:
        #     subscriptions.parse_subscription(event, self.vk_connection_admin, True)
        # elif event.type == VkBotEventType.GROUP_LEAVE:
        #     subscriptions.parse_subscription(event, self.vk_connection_admin, False)

    def _get_keyboard(self, keyboard_name, post_id):
        # print(os.listdir("./"))
        keyboard = open(f'keyboards/{keyboard_name}.json', "r", encoding="UTF-8").read()
        keyboard = json.loads(keyboard)
        for elem in keyboard['buttons']:
            elem[0]['action']['payload']["post_id"] = str(post_id)
        keyboard = json.dumps(keyboard, ensure_ascii=False)
        return keyboard

    def start_consuming(self):
        conn_params = pika.ConnectionParameters(self.rabbitmq_host, self.rabbitmq_port)
        connection = pika.BlockingConnection(conn_params)
        channel = connection.channel()
        queue_name = f'{self.queue_name_prefix}_new_suggested_post'
        channel.queue_declare(queue=queue_name,
                              durable=True)
        while True:
            status, properties, message = channel.basic_get(queue=queue_name, auto_ack=True)
            if message is None:
                break
            else:
                message_text = message.decode()
                logger.info(f'Получено новое сообщение от брокера {message_text}')
                self.add_new_message_post(message_text)

        connection.close()

    def add_new_message_post(self, post_id):

        try:
            post = Post.get(id=post_id)
        except Post.PostDoesNotExist:
            logger.warning(f'Не найден пост с ID={post_id}')
            return

        message_id = self.vk.messages.send(peer_id=self.chat_for_suggest,
                                           message=self._get_post_present(post),
                                           keyboard=self._get_keyboard("new_post", post_id),
                                           random_id=random.randint(10 ** 5, 10 ** 6),
                                           attachment=[str(att.attachment) for att in post.attachments])

        message_of_post = MessageOfSuggestedPost.create(post_id=post_id, message_id=message_id)

    @staticmethod
    def _get_post_present(post):
        present = f'Новый пост от {post.user}\n' \
                  f'{post}\n' \
                  f'текст:\n' \
                  f'{post.text}\n'
        return present

    def run(self):
        # try:
        self._start_polling()
        # except Exception as ex:
        #     logger.error(ex)

    def run_in_loop(self):
        while True:
            self.run()
            sleep(60)


if __name__ == '__main__':
    server = Server()
    server.run_in_loop()
