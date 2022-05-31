import utils.config as config
from utils.config import logger
from vk_api import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from time import sleep
from BotVKPoster.PosterModels.MessagesOfSuggestedPosts import MessageOfSuggestedPost
from BotVKPoster.PosterModels.PublishedPosts import PublishedPost
from BotVKPoster.PosterModels import create_db
from utils.connection_holder import VKConnectionsHolder
from BotVKPoster import keyboards
import pika
import datetime
import json
import random
from Models.Posts import Post, PostsHashtag, PostStatus
from Models.Relations import PostsAttachment


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

        """
        События очереди из брокера проверяются после ожидания событий от ВК, но не чаще time_to_update_broker
        Время ожидания событий от вк задаётся параметром wait класса VkBotLongPoll
        """
        while True:
            # https://habr.com/ru/post/512412/
            # logger.info('Проверка событий ВК')
            for event in self._longpoll.check():
                # logger.info(f'обработка события ВК {event.type}')

                if event.type == VkBotEventType.MESSAGE_EVENT:
                    payload = event.object.get('payload', {})
                    if 'post_id' in payload:
                        """
                        ID сообщения при его отправке не совпадает с реальным ID сообщения.
                        Придётся фиксировать соответствие при нажатии пользователем на кнопку 
                        """
                        message_of_post = MessageOfSuggestedPost.get_or_create(
                            post_id=payload['post_id'],
                            message_id=event.object.get('conversation_message_id'))
                    if 'command' in payload:
                        self._proces_button_click(payload=payload,
                                                  message_id=event.object.get('conversation_message_id'),
                                                  admin_id=event.object.get('user_id'))
                elif event.type == VkBotEventType.MESSAGE_NEW:
                    if event.from_chat and str(event.object['message']['peer_id']) == str(self.chat_for_suggest):
                        if event.object.message['text'] == 'create_db':
                            create_db.create_all_tables()
            now = datetime.datetime.now()
            if not last_broker_update or (now - last_broker_update).total_seconds() >= time_to_update_broker:
                logger.info('Проверка событий очереди')
                self._start_consuming()
                last_broker_update = datetime.datetime.now()

    def _proces_button_click(self, payload: dict, message_id: int = None, admin_id: int = None):
        if payload['command'] == 'public_post':
            new_post_id = self._publish_post(post_id=payload['post_id'], admin_id=admin_id)
            self._update_message_post(post_id=payload['post_id'], message_id=message_id)
        if payload['command'] == 'show_main_menu':
            self._update_message_post(post_id=payload['post_id'], message_id=message_id)
        elif payload['command'] == 'edit_hashtags':
            self._show_hashtags_menu(post_id=payload['post_id'], message_id=message_id, page=payload.get('page', 1))
        elif payload['command'] == 'add_hashtag':
            self._add_hashtag(post_id=payload['post_id'], hashtag=payload['hashtag'])
            self._show_hashtags_menu(post_id=payload['post_id'], message_id=message_id, page=payload.get('page', 1))
        elif payload['command'] == 'remove_hashtag':
            self._remove_hashtag(post_id=payload['post_id'], hashtag=payload['hashtag'])
            self._show_hashtags_menu(post_id=payload['post_id'], message_id=message_id, page=payload.get('page', 1))

    def _publish_post(self, post_id: str, admin_id: int = None):
        try:
            post = Post.get(id=post_id)
        except Post.PostDoesNotExist:
            logger.warning(f'Не найден пост с ID={post_id}')
            return

        message = post.text

        hashtags = [str(hashtag.hashtag) for hashtag in post.hashtags]
        if len(hashtags) > 0:
            message = message + '\n' + '\n'.join(hashtags)

        attachment = [str(att.attachment) for att in post.attachments]

        new_post = self.vk_admin.wall.post(owner_id=-self.group_id,
                                           signed=0 if post.anonymously else 1,
                                           post_id=post.vk_id,
                                           message=message,
                                           attachments=attachment)
        new_post_id = Post.generate_id(owner_id=-self.group_id, vk_id=new_post['post_id'])

        post.suggest_status = PostStatus.POSTED.value
        post.is_deleted = True
        post.save()

        new_post_info = PublishedPost.create(
            suggested_post_id=post_id,
            published_post_id=new_post_id,
            admin_id=admin_id
        )

        return new_post_id

    def _start_consuming(self):
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
                self._add_new_message_post(message_text)

        connection.close()

    def _add_new_message_post(self, post_id):

        post = self._get_post_by_id(post_id=post_id)
        if not post:
            return

        message_id = self.vk.messages.send(peer_id=self.chat_for_suggest,
                                           message=self._get_post_description(post),
                                           keyboard=keyboards.main_menu_keyboard(post),
                                           random_id=random.randint(10 ** 5, 10 ** 6),
                                           attachment=[str(att.attachment) for att in post.attachments])

    def _update_message_post(self, post_id, message_id: int = None):

        post = self._get_post_by_id(post_id=post_id)
        message_id = self._get_posts_message_id(post_id, message_id)
        if not post or not message_id:
            return

        try:
            result = self.vk.messages.edit(peer_id=self.chat_for_suggest,
                                           conversation_message_id=message_id,
                                           message=self._get_post_description(post),
                                           keyboard=keyboards.main_menu_keyboard(post),
                                           attachment=[str(att.attachment) for att in post.attachments])
        except Exception as ex:
            logger.warning(f'Не удалось отредактировать сообщение ID={message_id} для поста ID={post_id}\n{ex}')

    def _show_hashtags_menu(self, post_id, message_id: int = None, page: int = 1):
        post = self._get_post_by_id(post_id=post_id)
        message_id = self._get_posts_message_id(post_id, message_id)
        if not post or not message_id:
            return

        text_message = self._get_post_description(post=post, with_hashtags=False)
        text_message += '\nВыберите хэштеги:'
        try:
            result = self.vk.messages.edit(peer_id=self.chat_for_suggest,
                                           conversation_message_id=message_id,
                                           message=text_message,
                                           keyboard=keyboards.hashtag_menu(post, page),
                                           attachment=[str(att.attachment) for att in post.attachments])
        except Exception as ex:
            logger.warning(f'Не удалось отредактировать сообщение ID={message_id} для поста ID={post_id}\n{ex}')

    def _add_hashtag(self, post_id, hashtag):
        post = self._get_post_by_id(post_id=post_id)
        if not post:
            return
        PostsHashtag.get_or_create(post=post, hashtag=hashtag)

    def _remove_hashtag(self, post_id, hashtag):
        post = self._get_post_by_id(post_id=post_id)
        if not post:
            return
        for ht in PostsHashtag.select().where(PostsHashtag.post == post, PostsHashtag.hashtag == hashtag):
            ht.delete_instance()

    @staticmethod
    def _get_posts_message_id(post_id, message_id: int = None):
        if not message_id:
            try:
                message_of_post = MessageOfSuggestedPost.get(post_id=post_id)
                message_id = message_of_post.message_id
            except MessageOfSuggestedPost.DoesNotExist:
                logger.warning(f'Не найдена информация о сообщении поста с ID={post_id}')
        return message_id

    @staticmethod
    def _get_post_by_id(post_id):
        try:
            return Post.get(id=post_id)
        except Post.DoesNotExist:
            logger.warning(f'Не найден пост с ID={post_id}')
            return

    @staticmethod
    def _get_post_description(post: Post, with_hashtags: bool = True):

        if post.suggest_status == PostStatus.SUGGESTED.value:
            text_status = f'Новый пост {post}'
        elif post.suggest_status == PostStatus.POSTED.value:
            if post.posted_in:
                post_url = str(post.posted_in)
            else:
                try:
                    new_post_record = PublishedPost.get(suggested_post_id=post.id)
                    post_url = Post.generate_url(post_id=new_post_record.published_post_id)
                except Exception as ex:
                    logger.error(f'Ошибка получения информации об опубликованном посте для {post}: {ex}')
                    post_url = ''

            text_status = '[ОПУБЛИКОВАН] ' + post_url
        elif post.suggest_status == PostStatus.REJECTED.value:
            text_status = '[ОТКЛОНЁН]'
        else:
            text_status = f'Неизвестный пост {post}'

        represent = f'{text_status}\n' \
                    f'автор: {post.user}\n' \
                    f'текст:\n' \
                    f'{post.text}\n'

        if with_hashtags:
            hashtags = [str(hashtag.hashtag) for hashtag in post.hashtags]
            if len(hashtags) > 0:
                represent = represent + '\n' + '\n'.join(hashtags)

        return represent

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
