import config as config
from config import logger
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from time import sleep
import pika
from Models.Posts import PostStatus
from Models import create_db
from utils.connection_holder import ConnectionsHolder

from Parser import comments, likes, posts, subscriptions, private_messages, _initial_downloading


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
            elif event.type == VkBotEventType.MESSAGE_NEW:
                if event.from_chat and str(event.object['message']['peer_id']) == str(self.chat_for_suggest):
                    if 'load_data' in event.object.message['text']:
                        if len(event.object.message['text'].split()) == 1:
                            group_id = self.group_id
                        else:
                            group_id = int(event.object.message['text'].split()[1])
                        _initial_downloading.load_all(self.vk_connection_admin, group_id)
                    if event.object.message['text'] == 'create_db':
                        create_db.create_all_tables()
                    elif event.object.message['text'] == 'recreate_db':
                        create_db.recreate_database()
                    elif event.object.message['text'] == 'lock_db':
                        create_db.lock_db()
                    elif event.object.message['text'] == 'unlock_db':
                        create_db.unlock_db()
                else:
                    message = private_messages.parse_private_message(event.object.message, self.vk_connection_admin)
                    self._send_alarm(message_type='new_private_message', message=message.id)
            elif event.type == VkBotEventType.MESSAGE_REPLY:
                if event.from_user:
                    private_messages.parse_private_message(event.object, self.vk_connection_admin)

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
