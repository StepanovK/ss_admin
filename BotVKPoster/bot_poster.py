import config as config
from config import logger, debug
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from time import sleep
from typing import Union, Optional
from PosterModels.MessagesOfSuggestedPosts import MessageOfSuggestedPost
from PosterModels.RepostedToConversationsPosts import RepostedToConversationPost
from PosterModels.PublishedPosts import PublishedPost
from PosterModels.SortedHashtags import SortedHashtag
from PosterModels import create_db
from utils.connection_holder import ConnectionsHolder
from utils.GettingUserInfo.getter import get_short_user_info
import keyboards
import pika
import datetime
import random
from Models.base import db as main_db
from Models.BanedUsers import BanedUser
from Models.Posts import Post, PostsHashtag, PostStatus
from Models.Users import User
from Models.Comments import Comment
from Models.ChatMessages import ChatMessage
from Models.Conversations import Conversation
from Models.ConversationMessages import ConversationMessage
from Models.Relations import PostsLike, CommentsLike
from Models.Subscriptions import Subscription
from Models.Admins import Admin
from Models.PrivateMessages import PrivateMessage
from utils.db_helper import queri_to_list
import utils.get_hasgtags as get_hasgtags
from utils.tg_auto_poster import MyAutoPoster
from utils import user_chek
from utils.GettingUserInfo import getter

MAX_MESSAGE_SIZE = 4048


class Server:
    vk_link = 'https://vk.com/'

    def __init__(self):
        self.group_id = config.group_id

        self.rabbitmq_host = config.rabbitmq_host
        self.rabbitmq_port = config.rabbitmq_port
        self.queue_name_prefix = config.queue_name_prefix

        self.chat_for_suggest = config.chat_for_suggest
        self.chat_for_comments_check = config.chat_for_comments_check

        self.vk_api_admin = ConnectionsHolder().vk_api_admin
        self.vk_admin = ConnectionsHolder().vk_connection_admin
        self.vk_api_group = ConnectionsHolder().vk_api_group
        self.vk = ConnectionsHolder().vk_connection_group
        self.tg_poster = None
        # try:
        #     self.tg_poster = MyAutoPoster()
        # except Exception as ex:
        #     logger.warning(f'Can`t connect to tg_poster: {ex}')
        self._checked_users = []

    def _start_polling(self):

        logger.info('Bot poster started!')

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
                        if event.object.payload.get('command').startswith('show_ui'):
                            getter.parse_event(event=event, vk_connection=self.vk)
                        else:
                            self._proces_button_click(payload=payload,
                                                      message_id=event.object.get('conversation_message_id'),
                                                      admin_id=event.object.get('user_id'))
                elif event.type == VkBotEventType.MESSAGE_NEW:
                    if event.from_chat and str(event.object['message']['peer_id']) == str(self.chat_for_suggest):
                        message_text = event.object.message['text']
                        if message_text == 'create_db' or message_text == 'recreate_db':
                            self.reconnect_db()

            now = datetime.datetime.now()
            if not last_broker_update or (now - last_broker_update).total_seconds() >= time_to_update_broker:
                if config.debug:
                    logger.info('Проверка сообщений брокера')
                self._start_consuming()
                last_broker_update = datetime.datetime.now()

            now = datetime.datetime.now()
            if not last_published_posts_update or (
                    now - last_published_posts_update).total_seconds() >= time_to_update_published_posts:
                if config.debug:
                    logger.info('Обновление опубликованных постов')
                self._update_published_posts()
                last_published_posts_update = datetime.datetime.now()

    def _start_consuming(self):
        channel = ConnectionsHolder().rabbit_connection.channel()
        self._rabbit_get_new_private_messages(channel)
        self._rabbit_get_new_posts(channel)
        self._rabbit_get_updated_posts(channel)
        self._rabbit_get_new_posted_posts(channel)
        self._rabbit_get_new_conversation_messages(channel)
        self._rabbit_get_new_comments(channel)
        self._rabbit_get_new_chat_messages(channel)
        self._rabbit_get_updated_chat_messages(channel)
        ConnectionsHolder().close_rabbit_connection()

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
                    users_suggested_posts = Post.select().where((Post.user == pm.user) &
                                                                (Post.suggest_status == PostStatus.SUGGESTED.value) &
                                                                (Post.is_deleted == False)).order_by(Post.date.desc())
                    max_count_to_update = 5
                    current_number = 1
                    for users_post in users_suggested_posts:
                        if current_number > max_count_to_update:
                            break
                        self._update_message_post(users_post.id)
                        current_number += 1

    def _rabbit_get_new_posted_posts(self, channel):
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
                if self.tg_poster is not None:
                    self.tg_poster.send_new_post(message_text)

    def _rabbit_get_new_conversation_messages(self, channel):
        queue_name = f'{self.queue_name_prefix}_new_conversation_message'
        channel.queue_declare(queue=queue_name,
                              durable=True)
        while True:
            status, properties, message = channel.basic_get(queue=queue_name, auto_ack=True)
            if message is None:
                break
            else:
                message_text = message.decode()
                self._update_reposted_conversation_message(message_text)

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
            published_post = _get_post_by_id(post_id=post_inf.published_post_id)
            suggested_post = _get_post_by_id(post_id=post_inf.suggested_post_id)
            if published_post and suggested_post:
                published_post.user = suggested_post.user
                if post_inf.admin_id:
                    admin_user, _ = User.get_or_create(id=post_inf.admin_id)
                    published_post.posted_by, _ = Admin.get_or_create(user=admin_user)
                published_post.save()

                post_inf.delete_instance()

                suggested_post.posted_in = published_post
                suggested_post.anonymously = published_post.anonymously
                suggested_post.marked_as_ads = published_post.marked_as_ads
                suggested_post.is_deleted = False  # На случай если он уже успел отметиться как удаленный
                suggested_post.save()
                with main_db.atomic():
                    for ht in PostsHashtag.select().where(PostsHashtag.post == suggested_post):
                        PostsHashtag.get_or_create(post=published_post, hashtag=ht.hashtag)

                self._delete_sorted_hashtags(post_id=post_inf.suggested_post_id)

    def _update_reposted_conversation_message(self, conversation_message_id):
        try:
            repost_inf = RepostedToConversationPost.get(conversation_message_id=conversation_message_id)
        except RepostedToConversationPost.DoesNotExist:
            return

        post = _get_post_by_id(post_id=repost_inf.post_id)
        if not post:
            return

        try:
            conversation_message = ConversationMessage.get(id=conversation_message_id)
        except RepostedToConversationPost.DoesNotExist:
            return

        conversation_message.from_post = post
        conversation_message.save()

        repost_inf.delete_instance()

    def _rabbit_get_new_comments(self, channel):
        queue_name = f'{self.queue_name_prefix}_new_comments'
        channel.queue_declare(queue=queue_name,
                              durable=True)
        while True:
            status, properties, message = channel.basic_get(queue=queue_name, auto_ack=True)
            if message is None:
                break
            else:
                message_text = message.decode()
                if config.debug:
                    logger.info(f'new_comment {message_text}')
                try:
                    comment = Comment.get(id=int(message_text))
                except Exception as ex:
                    logger.warning(f'comment id={message_text} is not found! {ex}')
                    continue
                self._check_comment_danger(comment)

    def _check_comment_danger(self, comment: Comment):
        user = comment.user
        if user not in self._checked_users:
            user_danger_degree = user_chek.get_degree_of_user_danger(user)
            if user_danger_degree >= 10:
                try:
                    self.vk.messages.send(peer_id=self.chat_for_comments_check,
                                          message=self._get_danger_comment_description(comment,
                                                                                       user_danger_degree),
                                          random_id=random.randint(10 ** 5, 10 ** 6),
                                          )
                except Exception as ex:
                    logger.warning(f'Failed send message peer_id={self.chat_for_comments_check}\n{ex}')

                getter.send_user_info(user=user,
                                      vk_connection=self.vk,
                                      peer_id=self.chat_for_comments_check)

            self._checked_users.append(user)

    def _rabbit_get_new_chat_messages(self, channel):
        queue_name = f'{self.queue_name_prefix}_new_chat_message'
        channel.queue_declare(queue=queue_name,
                              durable=True)
        while True:
            status, properties, message = channel.basic_get(queue=queue_name, auto_ack=True)
            if message is None:
                break
            else:
                message_text = message.decode()
                if config.debug:
                    logger.info(f'new_chat_message {message_text}')
                try:
                    chat_message = ChatMessage.get(id=message_text)
                except Exception as ex:
                    logger.warning(f'chat_message id={message_text} is not found! {ex}')
                    continue
                self._check_chat_message_danger(chat_message)

    def _rabbit_get_updated_chat_messages(self, channel):
        queue_name = f'{self.queue_name_prefix}_updated_chat_message'
        channel.queue_declare(queue=queue_name,
                              durable=True)
        while True:
            status, properties, message = channel.basic_get(queue=queue_name, auto_ack=True)
            if message is None:
                break
            else:
                message_text = message.decode()
                if config.debug:
                    logger.info(f'updated_chat_message {message_text}')
                try:
                    chat_message = ChatMessage.get(id=message_text)
                except Exception as ex:
                    logger.warning(f'chat_message id={message_text} is not found! {ex}')
                    continue
                self._check_chat_message_danger(chat_message)

    def _check_chat_message_danger(self, chat_message: ChatMessage):
        user = chat_message.user
        if user not in self._checked_users:
            user_danger_degree = user_chek.get_degree_of_user_danger(user)
            if user_danger_degree >= 15:
                chat = chat_message.chat
                mark_as_spam = user_danger_degree > 15
                message_is_deleted = False
                try:
                    spam = 1 if mark_as_spam and not debug else 0,
                    result = self.vk_admin.messages.delete(
                        peer_id=chat.chat_id,
                        spam=spam,
                        group_id=self.group_id,
                        delete_for_all=1,
                        cmids=str(chat_message.message_id),
                    )
                    if isinstance(result, dict) and result.get(str(chat_message.message_id)) == 1:
                        message_is_deleted = True
                        logger.warning(f'Spam chat message in {chat} is deleted!\nText: {chat_message.text}')
                except Exception as ex:
                    logger.error(f'Failed delete chat message {chat_message}\n{ex}')

                if message_is_deleted:
                    try:
                        spam_text = ' и отмечено как спам' if mark_as_spam else ''
                        self.vk.messages.send(
                            peer_id=chat.chat_id,
                            message=f'Сообщение от пользователя {chat_message.user} удалено ботом{spam_text}!',
                            random_id=random.randint(10 ** 5, 10 ** 6),
                        )
                    except Exception as ex:
                        logger.error(f'Failed to send chat message in {chat}\n{ex}')
                    try:
                        self.vk.messages.send(peer_id=self.chat_for_comments_check,
                                              message=f'Удалён спам от {user} в чате {chat}\n'
                                                      f'Текст: {chat_message.text}',
                                              random_id=random.randint(10 ** 5, 10 ** 6),
                                              )
                    except Exception as ex:
                        logger.error(f'Failed to send chat message in chat_for_comments_check\n{ex}')
            elif user_danger_degree >= 10:
                try:
                    self.vk.messages.send(peer_id=self.chat_for_comments_check,
                                          message=self._get_danger_chat_message_description(chat_message,
                                                                                            user_danger_degree),
                                          random_id=random.randint(10 ** 5, 10 ** 6),
                                          )
                except Exception as ex:
                    logger.warning(f'Failed send message peer_id={self.chat_for_comments_check}\n{ex}')

            else:
                self._checked_users.append(user)

    @staticmethod
    def _get_danger_comment_description(comment, user_danger_degree):
        return f'Комментарий от подозрительного пользователя {comment.user} (оценка опасности: {user_danger_degree})\n' \
               f'{comment.get_url()}\n' \
               f'Текст: {comment.text}'

    @staticmethod
    def _get_danger_chat_message_description(chat_message, user_danger_degree):
        return f'Сообщение в чате {chat_message.chat} от подозрительного пользователя {chat_message.user}' \
               f' (оценка опасности: {user_danger_degree})\n' \
               f'Текст: {chat_message.text}'

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
        elif payload['command'] == 'show_conversation_menu':
            self._show_conversation_menu(post_id=payload['post_id'], message_id=message_id, page=payload.get('page', 1))
        elif payload['command'] == 'add_hashtag':
            self._add_hashtag(post_id=payload['post_id'], hashtag=payload['hashtag'])
            self._show_hashtags_menu(post_id=payload['post_id'], message_id=message_id, page=payload.get('page', 1))
        elif payload['command'] == 'ban_user_from_suggest_post':
            self._ban_from_suggest_post(post_id=payload['post_id'], reason=payload['reason'],
                                        admin_id=admin_id, report_type=payload.get('report_type', ''))
            self._show_ban_menu(post_id=payload['post_id'], message_id=message_id)
        elif payload['command'] == 'remove_hashtag':
            self._remove_hashtag(post_id=payload['post_id'], hashtag=payload['hashtag'])
            self._show_hashtags_menu(post_id=payload['post_id'], message_id=message_id, page=payload.get('page', 1))
        elif payload['command'] == 'show_user_info':
            self._show_user_info(post_id=payload['post_id'], message_id=message_id)
        elif payload['command'] == 'show_ban_from_post_menu':
            self._show_ban_menu(post_id=payload['post_id'], message_id=message_id)
        elif payload['command'] == 'repost_to_conversation':
            self._repost_to_conversation(post_id=payload['post_id'], conversation_id=payload['conversation_id'])
            self._show_conversation_menu(post_id=payload['post_id'], message_id=message_id, page=payload.get('page', 1))
        elif payload['command'] == 'set_anonymously':
            self._set_anonymously(post_id=payload['post_id'], value=payload['val'])
            self._update_message_post(post_id=payload['post_id'], message_id=message_id)
        elif payload['command'] == 'update_post':
            self._update_message_post(post_id=payload['post_id'], message_id=message_id)

    def _publish_post(self, post_id: str, admin_id: int = None):
        post = _get_post_by_id(post_id=post_id)
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
            return None

        new_post_id = Post.generate_id(owner_id=-self.group_id, vk_id=new_post['post_id'])

        post.suggest_status = PostStatus.POSTED.value
        if admin_id:
            post.posted_by = server._get_admin_by_vk_id(admin_id)
        post.is_deleted = True
        post.save()

        new_post_info = PublishedPost.create(
            suggested_post_id=post_id,
            published_post_id=new_post_id,
            admin_id=admin_id
        )

        return new_post_id

    def _reject_post(self, post_id: str, admin_id: int = None):
        post = _get_post_by_id(post_id=post_id)
        if not post:
            return

        try:
            result = self.vk_admin.wall.delete(owner_id=-self.group_id, post_id=post.vk_id)
        except Exception as ex:
            logger.warning(f'Failed to reject post {post}: {ex}')
            result = None

        if result == 1:
            post.suggest_status = PostStatus.REJECTED.value
            post.is_deleted = True
            if admin_id:
                admin_user, _ = User.get_or_create(id=admin_id)
                post.posted_by, _ = Admin.get_or_create(user=admin_user)
            post.save()

            self._delete_sorted_hashtags(post_id=post.id)

    def _add_new_message_post(self, post_id):

        post = _get_post_by_id(post_id=post_id)
        if not post:
            return

        self._update_sorted_hashtags(post)
        self._add_most_common_hashtag(post)
        self._set_anonymously_by_post_text(post)

        message_id = self.vk.messages.send(peer_id=self.chat_for_suggest,
                                           message=_get_post_description(post),
                                           keyboard=keyboards.main_menu_keyboard(post),
                                           random_id=random.randint(10 ** 5, 10 ** 6),
                                           attachment=[str(att.attachment) for att in post.attachments])

    @staticmethod
    def _add_most_common_hashtag(post: Post):
        for hashtag in SortedHashtag.select().where(SortedHashtag.post_id == post.id).limit(1):
            if hashtag.rating is not None and hashtag.rating > 1:
                PostsHashtag.get_or_create(post=post, hashtag=hashtag.hashtag)

    def _update_message_post(self, post_id, message_id: int = None):

        post = _get_post_by_id(post_id=post_id)
        message_id = self._get_posts_message_id(post_id, message_id)
        if not post or not message_id:
            return

        try:
            result = self.vk.messages.edit(peer_id=self.chat_for_suggest,
                                           conversation_message_id=message_id,
                                           message=_get_post_description(post),
                                           keyboard=keyboards.main_menu_keyboard(post),
                                           attachment=[str(att.attachment) for att in post.attachments])
        except Exception as ex:
            logger.warning(f'Failed to edit message ID={message_id} for post ID={post_id}\n{ex}')

    def _show_hashtags_menu(self, post_id, message_id: int = None, page: int = 1):
        post = _get_post_by_id(post_id=post_id)
        message_id = self._get_posts_message_id(post_id, message_id)
        if not post or not message_id:
            return

        text_message = _get_post_description(post=post, with_hashtags=False)
        text_message += '\nВыберите хэштеги:'
        try:
            result = self.vk.messages.edit(peer_id=self.chat_for_suggest,
                                           conversation_message_id=message_id,
                                           message=text_message,
                                           keyboard=keyboards.hashtag_menu(post, page),
                                           )
        except Exception as ex:
            logger.warning(f'Failed to edit message ID={message_id} for post ID={post_id}\n{ex}')

    def _show_conversation_menu(self, post_id, message_id: int = None, page: int = 1):
        post = _get_post_by_id(post_id=post_id)
        message_id = self._get_posts_message_id(post_id, message_id)
        if not post or not message_id:
            return

        text_message = _get_post_description(post=post, with_hashtags=False)
        text_message += '\nВыберите обсуждение:'
        try:
            result = self.vk.messages.edit(peer_id=self.chat_for_suggest,
                                           conversation_message_id=message_id,
                                           message=text_message,
                                           keyboard=keyboards.conversation_menu(post, page),
                                           )
        except Exception as ex:
            logger.warning(f'Failed to edit message ID={message_id} for post ID={post_id}\n{ex}')

    @staticmethod
    def _add_hashtag(post_id, hashtag):
        post = _get_post_by_id(post_id=post_id)
        if not post:
            return
        PostsHashtag.get_or_create(post=post, hashtag=hashtag)

    def _ban_from_suggest_post(self, post_id, reason, admin_id, report_type):

        post = _get_post_by_id(post_id=post_id)
        if not post:
            return

        getter.ban_user_with_report(vk_connection_admin=self.vk_admin,
                                    user=post.user,
                                    reason=reason,
                                    report_type=report_type,
                                    comment=str(post),
                                    admin=_get_admin_by_vk_id(admin_id))

    @staticmethod
    def _remove_hashtag(post_id, hashtag):
        post = _get_post_by_id(post_id=post_id)
        if not post:
            return
        for ht in PostsHashtag.select().where((PostsHashtag.post == post)
                                              & (PostsHashtag.hashtag == hashtag)):
            ht.delete_instance()

    @staticmethod
    def _set_anonymously(post_id, value: bool = True):
        post = _get_post_by_id(post_id=post_id)
        if not post:
            return
        post.anonymously = value
        post.save()

    def _show_user_info(self, post_id, message_id: int = None):
        post = _get_post_by_id(post_id=post_id)
        if not post:
            return
        mes_text = get_short_user_info(post.user)

        try:
            result = self.vk.messages.edit(peer_id=self.chat_for_suggest,
                                           conversation_message_id=message_id,
                                           message=mes_text,
                                           keyboard=keyboards.user_info_menu(post))
        except Exception as ex:
            logger.warning(f'Failed to edit message ID={message_id} for post ID={post_id}\n{ex}')

    def _show_ban_menu(self, post_id, message_id: int):
        post = _get_post_by_id(post_id=post_id)
        if not post:
            return
        mes_text = f'Выберите причину блокировки пользователя {post.user}, предложившего пост {post}'

        try:
            result = self.vk.messages.edit(peer_id=self.chat_for_suggest,
                                           conversation_message_id=message_id,
                                           message=mes_text,
                                           keyboard=keyboards.user_ban_menu(post))
        except Exception as ex:
            logger.warning(f'Failed to edit message ID={message_id} for post ID={post_id}\n{ex}')

    def _repost_to_conversation(self, post_id, conversation_id):
        post = _get_post_by_id(post_id=post_id)
        if not post:
            return

        attachment = [str(att.attachment) for att in post.attachments]

        text_message = f'{post.user} писал(а):\n{post.text}'

        conversation = Conversation.get(id=conversation_id)

        try:
            new_conv_message_id = self.vk_admin.board.createComment(group_id=self.group_id,
                                                                    topic_id=conversation.conversation_id,
                                                                    post_id=post.vk_id,
                                                                    message=text_message,
                                                                    attachments=attachment,
                                                                    from_group=1,
                                                                    guid=str(random.randint(10 ** 5, 10 ** 6))
                                                                    )
        except Exception as ex:
            logger.warning(f'Failed to repost to conversation ID={conversation_id} post ID={post.vk_id}\n{ex}')
            return None

        reposting_record, _ = RepostedToConversationPost.get_or_create(
            post_id=post_id,
            conversation_id=f'{conversation_id}',
            conversation_message_id=f'{conversation_id}_{new_conv_message_id}',
        )

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
    def _set_anonymously_by_post_text(post: Post, save_post: bool = True):
        l_text = post.text.lower()
        anon_words = ['анон', 'ононимн', 'ананимн']
        for anon_w in anon_words:
            if anon_w in l_text:
                post.anonymously = True
                if save_post:
                    post.save()

    @staticmethod
    def _update_sorted_hashtags(post):
        Server._delete_sorted_hashtags(post_id=post.id)

        ht_and_post = [(ht, rating, post.id) for ht, rating in get_hasgtags.get_sorted_hashtags(post)]
        SortedHashtag.insert_many(ht_and_post, fields=[SortedHashtag.hashtag,
                                                       SortedHashtag.rating,
                                                       SortedHashtag.post_id]).execute()

    @staticmethod
    def _delete_sorted_hashtags(post_id: str):
        SortedHashtag.delete().where(SortedHashtag.post_id == post_id).execute()

    @staticmethod
    def reconnect_db():
        try:
            main_db.close()
            logger.info('Disconnected from DB')
            sleep(10)
            main_db.connect()
            logger.info('Connected to DB')
        except Exception as ex:
            logger.warning(f'Can`t reconnect to DB! {ex}')

    def run(self):
        if config.debug:
            self._start_polling()
        else:
            try:
                self._start_polling()
            except Exception as ex:
                logger.error(ex)

    def run_in_loop(self):
        while True:
            self.run()
            sleep(10)


def _get_admin_by_vk_id(admin_id):
    admin_user, _ = User.get_or_create(id=admin_id)
    admin, _ = Admin.get_or_create(user=admin_user)
    return admin


def _get_post_by_id(post_id) -> Union[Post, None]:
    try:
        return Post.get(id=post_id)
    except Post.DoesNotExist:
        logger.warning(f'Post not found ID={post_id}')


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

    if post.posted_by is not None:
        text_status += f'\nадмином: {post.posted_by}'

    message_text = ''
    p_messages = PrivateMessage.select(
    ).where((PrivateMessage.user == post.user)
            & (PrivateMessage.admin.is_null())).order_by(PrivateMessage.date.desc())
    user_comment = post.user.comment
    if user_comment is not None and user_comment != '':
        message_text += f'({user_comment})' + '\n'
    if len(p_messages) > 0:
        last_message = p_messages[0]
        message_text += f'Писал в ЛС группы {last_message.date:%Y.%m.%d}\n' \
                        f'Чат: {last_message.get_chat_url()}'

        admin_messages = PrivateMessage.select(
        ).join(Admin).where((PrivateMessage.user == post.user)
                            & (PrivateMessage.admin.is_null(False))
                            & (Admin.is_bot == False)).order_by(PrivateMessage.date.desc())
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
            represent = represent + '\n'.join(hashtags)

    if len(represent) > MAX_MESSAGE_SIZE:
        represent_without_text = represent.replace(post.text, '')
        represent = represent.replace(
            post.text,
            post.text[:(MAX_MESSAGE_SIZE - len(represent_without_text) - 3)] + '...'
        )

    return represent


if __name__ == '__main__':
    create_db.check_or_create_db()
    server = Server()
    server.run_in_loop()
