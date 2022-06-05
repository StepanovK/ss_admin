import utils.config as config
from utils.config import logger
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from time import sleep
import pika
from Models.Posts import PostStatus
from utils.connection_holder import ConnectionsHolder

from BotVKListener.Parser import comments, likes, posts, subscriptions


class Server:
    vk_link = 'https://vk.com/'

    def __init__(self):
        self.group_id = config.group_id

        self.rabbitmq_host = config.rabbitmq_host
        self.rabbitmq_port = config.rabbitmq_port
        self.queue_name_prefix = config.queue_name_prefix

        self.chat_for_suggest = config.chat_for_suggest

        self.vk_api_admin = ConnectionsHolder().vk_api_admin
        self.vk_connection_admin = ConnectionsHolder().vk_connection_admin
        self.vk_api_group = ConnectionsHolder().vk_api_group
        self.vk_connection_group = ConnectionsHolder().vk_connection_group

    def _start_polling(self):
        self._longpoll = VkBotLongPoll(self.vk_api_group, self.group_id, )

        logger.info('Бот запущен')

        for event in self._longpoll.listen():

            logger.info(f'Новое событие {event.type}')
            if event.type == VkBotEventType.WALL_POST_NEW:
                new_post = posts.parse_wall_post(event.object, self.vk_connection_admin)
                str_from_user = '' if new_post.user is None else f'от {new_post.user} '
                str_attachments = '' if len(new_post.attachments) == 0 else f', вложений: {len(new_post.attachments)}'
                str_action = 'Опубликован пост' if new_post.suggest_status is None else 'В предложке новый пост'
                logger.info(f'{str_action} {str_from_user}{new_post}{str_attachments}')
                if self.queue_name_prefix != '' and new_post.suggest_status == PostStatus.SUGGESTED.value:
                    self._send_alarm(message_type='new_suggested_post', message=new_post.id)
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

    def _send_alarm(self, message_type: str, message: str):
        credentials = pika.PlainCredentials('guest', 'guest')
        conn_params = pika.ConnectionParameters(host=self.rabbitmq_host,
                                                port=self.rabbitmq_port,
                                                credentials=credentials)
        connection = pika.BlockingConnection(conn_params)
        channel = connection.channel()
        queue_name = f'{self.queue_name_prefix}_{message_type}'
        channel.queue_declare(queue=queue_name,
                              durable=True)
        channel.basic_publish(exchange='',
                              routing_key=queue_name,
                              body=message.encode(),
                              properties=pika.BasicProperties(delivery_mode=2))
        connection.close()

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
