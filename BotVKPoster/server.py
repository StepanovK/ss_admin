import config as config
from config import logger
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from time import sleep
from PosterModels.MessagesOfSuggestedPosts import MessageOfSuggestedPost
from PosterModels.PublishedPosts import PublishedPost
from PosterModels.SortedHashtags import SortedHashtag
from PosterModels import create_db
from utils.connection_holder import ConnectionsHolder
import keyboards
import pika
import datetime
import random
from Models.base import db as main_db
from Models.Posts import Post, PostsHashtag, PostStatus
from Models.Users import User
from Models.Comments import Comment
from Models.Relations import PostsLike, CommentsLike
from Models.Subscriptions import Subscription
from Models.Admins import Admin
from Models.PrivateMessages import PrivateMessage
from utils.db_helper import queri_to_list
import utils.get_hasgtags as get_hasgtags
from utils.tg_auto_poster import MyAutoPoster


class Server:
    vk_link = 'https://vk.com/'

    def __init__(self):
        self.group_id = config.group_id

        self.rabbitmq_host = config.rabbitmq_host
        self.rabbitmq_port = config.rabbitmq_port
        self.queue_name_prefix = config.queue_name_prefix

        self.chat_for_suggest = config.chat_for_suggest

        self.vk_api_admin = ConnectionsHolder().vk_api_admin
        self.vk_admin = ConnectionsHolder().vk_connection_admin
        self.vk_api_group = ConnectionsHolder().vk_api_group
        self.vk = ConnectionsHolder().vk_connection_group
        self.tg_poster = MyAutoPoster()
        self.rabbit_connection = ConnectionsHolder().rabbit_connection

    def _start_polling(self):

        logger.info('Bot started!')

        self._longpoll = VkBotLongPoll(self.vk_api_group, self.group_id, wait=5)

        time_to_update_broker = 10
        last_broker_update = None

        time_to_update_published_posts = 30
        last_published_posts_update = None

        """
        События очереди из брокера проверяются после ожидания событий от ВК, но не чаще time_to_update_broker
        Время ожидания событий от вк задаётся параметром wait класса VkBotLongPoll
        С периодичностью time_to_update_published_posts в предложенных постах записывается ID опубликованных 
        """
        while True:
            # https://habr.com/ru/post/512412/
            for event in self._longpoll.check():
                # logger.info(f'обработка события ВК {event.type}')

                if event.type == VkBotEventType.MESSAGE_EVENT:
                    payload = event.object.get('payload', {})
                    if 'post_id' in payload:
                        """
                        ID сообщения при его отправке не совпадает с реальным ID сообщения.
                        Придётся фиксировать соответствие при нажатии пользователем на кнопку 
                        """
                        message_of_post, _ = MessageOfSuggestedPost.get_or_create(
                            post_id=payload['post_id'],
                            message_id=event.object.get('conversation_message_id'))
                    if 'command' in payload:
                        self._proces_button_click(payload=payload,
                                                  message_id=event.object.get('conversation_message_id'),
                                                  admin_id=event.object.get('user_id'))

            now = datetime.datetime.now()
            if not last_broker_update or (now - last_broker_update).total_seconds() >= time_to_update_broker:
                # logger.info('Проверка новых постов')
                self._start_consuming()
                last_broker_update = datetime.datetime.now()

            now = datetime.datetime.now()
            if not last_published_posts_update or (
                    now - last_published_posts_update).total_seconds() >= time_to_update_published_posts:
                # logger.info('Обновление опубликованных постов')
                self._update_published_posts()
                last_published_posts_update = datetime.datetime.now()

    def _start_consuming(self):
        channel = self.rabbit_connection.channel()
        self._rabbit_get_new_private_messages(channel)
        self._rabbit_get_new_posts(channel)
        self._rabbit_get_updated_posts(channel)
        self._rabbit_new_posted_posts(channel)

    def _rabbit_get_new_posts(self, channel):
        queue_name = f'{self.queue_name_prefix}_new_suggested_post'
        channel.queue_declare(queue=queue_name,
                              durable=True)
        while True:
            status, properties, message = channel.basic_get(queue=queue_name, auto_ack=True)
            if message is None:
                break
            else:
                message_text = message.decode()
                logger.info(f'new_suggested_post {message_text}')
                self._add_new_message_post(message_text)

    def _rabbit_get_new_private_messages(self, channel):
        queue_name = f'{self.queue_name_prefix}_new_private_message'
        channel.queue_declare(queue=queue_name,
                              durable=True)
        while True:
            status, properties, message = channel.basic_get(queue=queue_name, auto_ack=True)
            if message is None:
                break
            else:
                message_text = message.decode()
                logger.info(f'new_private_message {message_text}')
                pm = None
                try:
                    pm = PrivateMessage.get(id=message_text)
                except PrivateMessage.DoesNotExist:
                    logger.warning(f'can`t find private message {message_text}!')
                    continue
                if pm:
                    users_suggested_posts = Post.select().where(Post.user == pm.user and
                                                                Post.suggest_status == PostStatus.SUGGESTED.value and
                                                                Post.is_deleted == False).order_by(Post.date.desc())
                    max_count_to_update = 5
                    current_number = 1
                    for users_post in users_suggested_posts:
                        if current_number > max_count_to_update:
                            break
                        self._update_message_post(users_post.id)
                        current_number += 1

    def _rabbit_new_posted_posts(self, channel):
        queue_name = f'{self.queue_name_prefix}_new_posted_post'
        channel.queue_declare(queue=queue_name,
                              durable=True)
        while True:
            status, properties, message = channel.basic_get(queue=queue_name, auto_ack=True)
            if message is None:
                break
            else:
                message_text = message.decode()
                logger.info(f'new_posted_post {message_text}')
                self.tg_poster.send_new_post(message_text)

    def _rabbit_get_updated_posts(self, channel):
        queue_name = f'{self.queue_name_prefix}_updated_posts'
        channel.queue_declare(queue=queue_name,
                              durable=True)
        while True:
            status, properties, message = channel.basic_get(queue=queue_name, auto_ack=True)
            if message is None:
                break
            else:
                message_text = message.decode()
                logger.info(f'updated_posts {message_text}')
                self._update_message_post(post_id=message_text)

    def _update_published_posts(self):
        for post_inf in PublishedPost.select():
            published_post = self._get_post_by_id(post_id=post_inf.published_post_id)
            suggested_post = self._get_post_by_id(post_id=post_inf.suggested_post_id)
            if published_post and suggested_post:
                published_post.user = suggested_post.user
                if post_inf.admin_id:
                    admin_user, _ = User.get_or_create(id=post_inf.admin_id)
                    published_post.posted_by, _ = Admin.get_or_create(user=admin_user)
                published_post.save()

                post_inf.delete_instance()

                suggested_post.posted_in = published_post
                suggested_post.save()
                with main_db.atomic():
                    for ht in PostsHashtag.select().where(PostsHashtag.post == suggested_post):
                        PostsHashtag.get_or_create(post=published_post, hashtag=ht.hashtag)

                SortedHashtag.delete().where(SortedHashtag.post_id == post_inf.suggested_post_id).execute()

    def _proces_button_click(self, payload: dict, message_id: int = None, admin_id: int = None):
        if payload['command'] == 'publish_post':
            new_post_id = self._publish_post(post_id=payload['post_id'], admin_id=admin_id)
            self._update_message_post(post_id=payload['post_id'], message_id=message_id)
        elif payload['command'] == 'reject_post':
            self._reject_post(post_id=payload['post_id'], admin_id=admin_id)
            self._update_message_post(post_id=payload['post_id'], message_id=message_id)
        elif payload['command'] == 'show_main_menu':
            self._update_message_post(post_id=payload['post_id'], message_id=message_id)
        elif payload['command'] == 'edit_hashtags':
            self._show_hashtags_menu(post_id=payload['post_id'], message_id=message_id, page=payload.get('page', 1))
        elif payload['command'] == 'add_hashtag':
            self._add_hashtag(post_id=payload['post_id'], hashtag=payload['hashtag'])
            self._show_hashtags_menu(post_id=payload['post_id'], message_id=message_id, page=payload.get('page', 1))
        elif payload['command'] == 'remove_hashtag':
            self._remove_hashtag(post_id=payload['post_id'], hashtag=payload['hashtag'])
            self._show_hashtags_menu(post_id=payload['post_id'], message_id=message_id, page=payload.get('page', 1))
        elif payload['command'] == 'show_user_info':
            self._show_user_info(post_id=payload['post_id'], message_id=message_id)
        elif payload['command'] == 'set_anonymously':
            self._set_anonymously(post_id=payload['post_id'], value=payload['val'])
            self._update_message_post(post_id=payload['post_id'], message_id=message_id)
        elif payload['command'] == 'update_post':
            self._update_message_post(post_id=payload['post_id'], message_id=message_id)

    def _publish_post(self, post_id: str, admin_id: int = None):
        post = self._get_post_by_id(post_id=post_id)
        if not post:
            return

        message = post.text

        hashtags = [str(hashtag.hashtag) for hashtag in post.hashtags]
        if len(hashtags) > 0:
            message = message + '\n' + '\n'.join(hashtags)

        attachment = [str(att.attachment) for att in post.attachments]

        try:
            new_post = self.vk_admin.wall.post(owner_id=-self.group_id,
                                               signed=0 if post.anonymously else 1,
                                               post_id=post.vk_id,
                                               message=message,
                                               attachments=attachment)
        except Exception as ex:
            logger.warning(f'Failed to publish post ID={post.vk_id}\n{ex}')
            return

        new_post_id = Post.generate_id(owner_id=-self.group_id, vk_id=new_post['post_id'])

        post.suggest_status = PostStatus.POSTED.value
        if admin_id:
            admin_user, _ = User.get_or_create(id=admin_id)
            post.posted_by, _ = Admin.get_or_create(user=admin_user)
        post.is_deleted = True
        post.save()

        new_post_info = PublishedPost.create(
            suggested_post_id=post_id,
            published_post_id=new_post_id,
            admin_id=admin_id
        )

        return new_post_id

    def _reject_post(self, post_id: str, admin_id: int = None):
        post = self._get_post_by_id(post_id=post_id)
        if not post:
            return

        result = self.vk_admin.wall.delete(owner_id=-self.group_id, post_id=post.vk_id)

        if result == 1:
            post.suggest_status = PostStatus.REJECTED.value
            post.is_deleted = True
            if admin_id:
                admin_user, _ = User.get_or_create(id=admin_id)
                post.posted_by, _ = Admin.get_or_create(user=admin_user)
            post.save()

            SortedHashtag.delete().where(SortedHashtag.post_id == post.id)

    def _add_new_message_post(self, post_id):

        post = self._get_post_by_id(post_id=post_id)
        if not post:
            return

        self._update_sorted_hashtags(post)

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
            logger.warning(f'Failed to edit message ID={message_id} for post ID={post_id}\n{ex}')

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
            logger.warning(f'Failed to edit message ID={message_id} for post ID={post_id}\n{ex}')

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

    def _set_anonymously(self, post_id, value: bool = True):
        post = self._get_post_by_id(post_id=post_id)
        if not post:
            return
        post.anonymously = value
        post.save()

    def _show_user_info(self, post_id, message_id: int = None):
        post = self._get_post_by_id(post_id=post_id)
        if not post:
            return
        subscribe_history = Subscription.select().where(Subscription.user == post.user).order_by(Subscription.date)
        subscribe_history_list = []
        for subscribe in subscribe_history:
            state = 'ПОДПИСАН' if subscribe.is_subscribed else 'ОТПИСАН'
            if subscribe.date is None:
                date_sub = '<Неизвестно когда>'
            elif subscribe.date == datetime.date(2000, 1, 1):
                date_sub = 'Давно'
            else:
                date_sub = f'{subscribe.date:%Y-%m-%d}'
            subscribe_history_list.append(f'{date_sub} {state}')

        mes_text = f'Информация о пользователе {post.user}:\n'

        if len(subscribe_history_list) == 0:
            mes_text += '\nПОЛЬЗОВАТЕЛЬ НЕ ПОДПИСАН!'
        else:
            mes_text += '\nИстория подписок: \n' + '\n'.join(subscribe_history_list) + '\n'

        published_posts = post.user.posts.where(Post.suggest_status == None).order_by(Post.date.desc()).limit(3)
        published_posts_list = []
        for users_post in published_posts:
            published_posts_list.append(f'{users_post} от {users_post.date:%Y-%m-%d}')
        if len(published_posts_list) > 0:
            mes_text += '\nПоследние опубликованные посты:\n' + '\n'.join(published_posts_list) + '\n'

        rejected_posts = post.user.posts.where((Post.suggest_status == PostStatus.REJECTED.value) | (
                Post.suggest_status == PostStatus.SUGGESTED.value)).order_by(
            Post.date.desc()).limit(3)
        rejected_posts_list = []
        for users_post in rejected_posts:
            rejected_posts_list.append(f'{users_post} от {users_post.date:%Y-%m-%d}')
        if len(rejected_posts_list) > 0:
            mes_text += '\nПоследние неопубликованные посты:\n' + '\n'.join(rejected_posts_list) + '\n'

        count_of_comments = len(post.user.comments)
        if count_of_comments > 0:
            mes_text += f'\nНаписал комментариев: {count_of_comments}\n'

        count_of_posts_likes = len(PostsLike.select().where(PostsLike.user == post.user))
        count_of_self_posts_likes = len(
            PostsLike.select().join(Post).where(
                (PostsLike.user == post.user) & (PostsLike.liked_object.user == post.user)))
        if count_of_posts_likes > 0:
            mes_text += f'\nЛайкнул постов: {count_of_posts_likes}'
            mes_text += '\n' if count_of_self_posts_likes == 0 else f' (в т.ч. своих: {count_of_self_posts_likes})\n'

        count_of_comments_likes = len(CommentsLike.select().where(CommentsLike.user == post.user))
        count_of_self_com_likes = len(
            CommentsLike.select().join(Comment).where(
                (CommentsLike.user == post.user) & (CommentsLike.liked_object.user == post.user)))
        if count_of_comments_likes > 0:
            mes_text += f'\nЛайкнул комментариев: {count_of_comments_likes}'
            mes_text += '\n' if count_of_self_com_likes == 0 else f' (в т.ч. своих: {count_of_self_com_likes})\n'

        try:
            result = self.vk.messages.edit(peer_id=self.chat_for_suggest,
                                           conversation_message_id=message_id,
                                           message=mes_text,
                                           keyboard=keyboards.user_info_menu(post))
        except Exception as ex:
            logger.warning(f'Failed to edit message ID={message_id} for post ID={post_id}\n{ex}')

    @staticmethod
    def _update_sorted_hashtags(post):
        SortedHashtag.delete().where(SortedHashtag.post_id == post.id).execute()

        ht_and_post = [(ht, post.id) for ht in get_hasgtags.get_sorted_hashtags(post)]
        SortedHashtag.insert_many(ht_and_post, fields=[SortedHashtag.hashtag, SortedHashtag.post_id]).execute()

    @staticmethod
    def _get_posts_message_id(post_id, message_id: int = None):
        if not message_id:
            try:
                message_of_post = MessageOfSuggestedPost.get(post_id=post_id)
                message_id = message_of_post.message_id
            except MessageOfSuggestedPost.DoesNotExist:
                logger.warning(f'Post message information not found! Post ID={post_id}')
        return message_id

    @staticmethod
    def _get_post_by_id(post_id):
        try:
            return Post.get(id=post_id)
        except Post.DoesNotExist:
            logger.warning(f'Post not found ID={post_id}')
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
                    logger.error(f'Error getting information about published post for {post}: {ex}')
                    post_url = ''
            anon_text = ' анонимно' if post.anonymously else ''
            text_status = f'[ОПУБЛИКОВАН{anon_text}] {post_url}'
        elif post.suggest_status == PostStatus.REJECTED.value:
            text_status = '[ОТКЛОНЁН]'
        else:
            text_status = f'Неизвестный пост {post}'

        message_text = ''
        p_messages = PrivateMessage.select(
        ).where(PrivateMessage.user == post.user
                and PrivateMessage.admin == None).order_by(PrivateMessage.date.desc())
        user_comment = post.user.comment
        if user_comment is not None and user_comment != '':
            message_text += f'({user_comment})' + '\n'
        if len(p_messages) > 0:
            last_message = p_messages[0]
            message_text += f'Писал в ЛС группы {last_message.date:%Y.%m.%d}\n' \
                            f'Чат: {last_message.get_chat_url()}'

            admin_messages = PrivateMessage.select(
            ).join(Admin).where(PrivateMessage.user == post.user
                                and PrivateMessage.admin != None
                                and Admin.is_bot == False).order_by(PrivateMessage.date.desc())
            if len(admin_messages) > 0:
                last_admin = admin_messages[0].admin
                message_text += '\n' + f'Последним общался {last_admin}'

            message_text = message_text + '\n'

        represent = f'{text_status}\n' \
                    f'Автор: {post.user}\n' \
                    f'{message_text}' \
                    f'Текст поста:\n' \
                    f'{post.text}\n'

        if with_hashtags:
            hashtags = [str(hashtag.hashtag) for hashtag in post.hashtags]
            if len(hashtags) > 0:
                represent = represent + '\n' + '\n'.join(hashtags)

        return represent

    def run(self):
        try:
            self._start_polling()
        except Exception as ex:
            logger.error(ex)

    def run_in_loop(self):
        while True:
            self.run()
            sleep(60)


if __name__ == '__main__':
    create_db.check_or_create_db()
    server = Server()
    server.run_in_loop()
