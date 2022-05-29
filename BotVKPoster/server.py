import utils.config as config
from utils.config import logger
from vk_api import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from time import sleep
from BotVKPoster.PosterModels.MessagesOfSuggestedPosts import MessageOfSuggestedPost
from BotVKPoster.PosterModels import create_db
from utils.connection_holder import VKConnectionsHolder
import pika


class Server:
    vk_link = 'https://vk.com/'

    def __init__(self):
        self.group_id = config.group_id

        self.rabbitmq_host = config.rabbitmq_host
        self.rabbitmq_port = config.rabbitmq_port
        self.queue_name_prefix = config.queue_name_prefix

        self.chat_for_suggest = config.chat_for_suggest

        self.vk_api_admin = VKConnectionsHolder().vk_api_admin
        self.vk_connection_admin = VKConnectionsHolder().vk_connection_admin
        self.vk_api_group = VKConnectionsHolder().vk_api_group
        self.vk_connection_group = VKConnectionsHolder().vk_connection_group

    def _start_polling(self):
        self._longpoll = VkBotLongPoll(self.vk_api_group, self.group_id)

        logger.info('Бот запущен')

        for event in self._longpoll.listen():
            logger.info(f'Новое событие {event.type}')
            if event.type == VkBotEventType.MESSAGE_NEW:
                if event.from_chat:
                    if str(event.object['message']['peer_id']) == str(self.chat_for_suggest):
                        if event.object['message']['text'] == 'create_db':
                            create_db.create_all_tables()

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

    def run(self):
        # try:
        self._start_polling()
        # except Exception as ex:
        #     logger.error(ex)

    def _callback(self, ch, method, properties, body):
        print(body)

    def start_consuming(self):
        conn_params = pika.ConnectionParameters(self.rabbitmq_host, self.rabbitmq_port)
        connection = pika.BlockingConnection(conn_params)
        channel = connection.channel()
        queue_name = f'{self.queue_name_prefix}_new_suggested_post'
        channel.queue_declare(queue=queue_name,
                              durable=True)

        print("Waiting for messages. To exit press CTRL+C")

        channel.basic_consume(queue=queue_name,
                              on_message_callback=self._callback,
                              auto_ack=True)

        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()
        except Exception as ex:
            channel.stop_consuming()
            logger.error(f'При получении сообщений rabbitmq возникла ошибка: {ex}')

    def run_in_loop(self):
        while True:
            self.run()
            sleep(60)


if __name__ == '__main__':
    server = Server()
    server.start_consuming()
    server.run_in_loop()
