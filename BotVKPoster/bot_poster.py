import config as config
from config import logger, debug
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from time import sleep
from typing import Union, Optional
import os.path
import requests
from PosterModels.MessagesOfSuggestedPosts import MessageOfSuggestedPost
from PosterModels.RepostedToConversationsPosts import RepostedToConversationPost
from PosterModels.PublishedPosts import PublishedPost
from PosterModels.SortedHashtags import SortedHashtag
from PosterModels.PostSettings import PostSettings
from PosterModels import create_db
from utils.connection_holder import ConnectionsHolder
from utils.GettingUserInfo.getter import get_short_user_info
import keyboards
import datetime
import threading
import random
from Models.base import db as main_db
from Models.Posts import Post, PostsHashtag, PostStatus
from Models.Users import User
from Models.Comments import Comment
from Models.ChatMessages import ChatMessage
from Models.Conversations import Conversation
from Models.ConversationMessages import ConversationMessage
from Models.Relations import PostsLike, CommentsLike
from Models.Subscriptions import Subscription
from Models.Admins import Admin, get_admin_by_vk_id
from Models.PrivateMessages import PrivateMessage
from Models.Relations import PostsAttachment
from Models.UploadedFiles import UploadedFile
import utils.get_hasgtags as get_hashtags
from utils.tg_auto_poster import MyAutoPoster
from utils import user_chek
from utils.GettingUserInfo import getter
from utils.rabbit_connector import get_messages_from_chanel, send_message, get_messages
from utils.watermark_creater import WatermarkCreator
from utils.Parser import attachments as attachment_parser
from utils import text_formatter

MAX_MESSAGE_SIZE = 4048
vk_link = 'https://vk.com/'


class Server:

    def __init__(self):
        self.group_id = config.group_id

        self.chat_for_suggest = config.chat_for_suggest
        self.chat_for_comments_check = config.chat_for_comments_check

        self.vk_api_admin = None
        self.vk_admin = None
        self.vk_api_group = None
        self.vk = None
        self.reconnect_vk()

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

        time_to_check_old_messages = 20
        last_check_old_messages = None

        time_to_healthcheck = config.healthcheck_interval / 4
        last_healthcheck = None

        """
        События очереди из брокера проверяются после ожидания событий от ВК, но не чаще time_to_update_broker
        Время ожидания событий от вк задаётся параметром wait класса VkBotLongPoll
        С периодичностью time_to_update_published_posts в предложенных постах записывается ID опубликованных 
        """
        while True:
            for event in self._longpoll.check():
                if event.type == VkBotEventType.MESSAGE_EVENT:
                    payload = event.object.get('payload', {})
                    if 'post_id' in payload:
                        """
                        ID сообщения при его отправке не совпадает с реальным ID сообщения.
                        Придётся фиксировать соответствие при нажатии пользователем на кнопку 
                        """
                        message_id = event.object.get('conversation_message_id')
                        post_id = payload['post_id']
                        message_of_post = _get_posts_message_record(post_id, message_id=message_id)
                        if message_of_post is None:
                            message_of_post = _get_posts_message_record(post_id, need_null_id=True)
                            if message_of_post is None:
                                date = self._get_date_of_post_message(peer_id=event.object['peer_id'],
                                                                      message_id=message_id)
                                date = datetime.datetime.now() if date is None else date
                                message_of_post = MessageOfSuggestedPost.create(post_id=post_id,
                                                                                message_id=message_id,
                                                                                message_date=date)
                            else:
                                message_of_post.message_id = message_id
                                message_of_post.save()

                    if 'command' in payload:
                        if event.object.payload.get('command').startswith('show_ui'):
                            getter.parse_event(event=event, vk_connection=self.vk, vk_connection_admin=self.vk_admin)
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
                self._run_in_thread(target=self._update_published_posts)
                last_published_posts_update = datetime.datetime.now()

            now = datetime.datetime.now()
            if not last_check_old_messages or (
                    now - last_check_old_messages).total_seconds() >= time_to_check_old_messages:
                if config.debug:
                    logger.info('Обновление старых сообщений в чате предложки')
                self._run_in_thread(target=self._update_old_messages_of_suggested_posts)
                last_check_old_messages = datetime.datetime.now()

            now = datetime.datetime.now()
            if not last_healthcheck or (now - last_healthcheck).total_seconds() >= time_to_healthcheck:
                self._run_in_thread(target=self._answer_healthcheck_messages)
                last_healthcheck = datetime.datetime.now()

    def _start_consuming(self):
        rabbit_connection = ConnectionsHolder().rabbit_connection
        if rabbit_connection:
            channel = rabbit_connection.channel()
            self._rabbit_get_new_private_messages(channel)
            self._rabbit_get_new_posts(channel)
            self._rabbit_get_updated_posts(channel)
            self._rabbit_get_new_posted_posts(channel)
            self._rabbit_get_new_conversation_messages(channel)
            self._rabbit_get_new_comments(channel)
            self._rabbit_get_new_chat_messages(channel)
            self._rabbit_get_updated_chat_messages(channel)
            ConnectionsHolder().close_rabbit_connection()
        else:
            logger.warning(f'Failed connect to rabbit!')

    def _rabbit_get_new_posts(self, channel):
        for message_text in get_messages_from_chanel(message_type='new_suggested_post', channel=channel):
            logger.info(f'new_suggested_post {message_text}')
            thread = threading.Thread(target=self._add_new_message_post, args=[message_text])
            thread.start()

    def _rabbit_get_new_private_messages(self, channel):
        for message_text in get_messages_from_chanel(message_type='new_private_message', channel=channel):
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
                    self._run_in_thread(target=self._update_message_post, args=[users_post.id])
                    current_number += 1

    def _rabbit_get_new_posted_posts(self, channel):
        for message_text in get_messages_from_chanel(message_type='new_posted_post', channel=channel):
            logger.info(f'new_posted_post {message_text}')
            if self.tg_poster is not None:
                self.tg_poster.send_new_post(message_text)

    def _rabbit_get_new_conversation_messages(self, channel):
        for message_text in get_messages_from_chanel(message_type='new_conversation_message', channel=channel):
            self._update_reposted_conversation_message(message_text)

    def _rabbit_get_updated_posts(self, channel):
        for message_text in get_messages_from_chanel(message_type='updated_posts', channel=channel):
            logger.info(f'updated_posts {message_text}')
            self._run_in_thread(target=self._update_message_post, args=[message_text])

    def _update_published_posts(self):
        for post_inf in PublishedPost.select():
            published_post = _get_post_by_id(post_id=post_inf.published_post_id, show_warning=False)
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

                self._update_message_post(suggested_post.id)

    @staticmethod
    def _answer_healthcheck_messages():
        message_type = f'{config.healthcheck_queue_name_prefix}_poster_requests'
        messages = get_messages(message_type=message_type)
        answer_message_type = f'{config.healthcheck_queue_name_prefix}_poster_answers'
        for message_text in messages:
            send_message(message_type=answer_message_type, message=message_text)

    @staticmethod
    def _update_reposted_conversation_message(conversation_message_id):
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
        for message_text in get_messages_from_chanel(message_type='new_comments', channel=channel):
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
            else:
                self._checked_users.append(user)

    def _rabbit_get_new_chat_messages(self, channel):
        for message_text in get_messages_from_chanel(message_type='new_chat_message', channel=channel):
            if config.debug:
                logger.info(f'new_chat_message {message_text}')
            try:
                chat_message = ChatMessage.get(id=message_text)
            except Exception as ex:
                logger.warning(f'chat_message id={message_text} is not found! {ex}')
                continue
            self._check_chat_message_danger(chat_message)

    def _rabbit_get_updated_chat_messages(self, channel):
        for message_text in get_messages_from_chanel(message_type='updated_chat_message', channel=channel):
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
            if user_danger_degree >= 13:
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
        elif payload['command'] == 'publish_post_pending':
            time_to_post = datetime.datetime.now() + datetime.timedelta(hours=1)
            new_post_id = self._publish_post(post_id=payload['post_id'], admin_id=admin_id, time_to_post=time_to_post)
            self._update_message_post(post_id=payload['post_id'], message_id=message_id)

        elif payload['command'] == 'reject_post':
            self._reject_post(post_id=payload['post_id'], admin_id=admin_id)
            self._update_message_post(post_id=payload['post_id'], message_id=message_id)
        elif payload['command'] == 'show_main_menu':
            self._update_message_post(post_id=payload['post_id'], message_id=message_id)
        elif payload['command'] == 'edit_hashtags':
            self._show_hashtags_menu(post_id=payload['post_id'], message_id=message_id, page=payload.get('page', 1))
        elif payload['command'] == 'clear_hashtags':
            self._delete_post_hashtags(payload['post_id'])
            self._update_message_post(post_id=payload['post_id'], message_id=message_id)
        elif payload['command'] == 'show_conversation_menu':
            self._show_conversation_menu(post_id=payload['post_id'], message_id=message_id, page=payload.get('page', 1))
        elif payload['command'] == 'add_hashtag':
            self._add_hashtag(post_id=payload['post_id'], hashtag=payload['hashtag'])
            self._show_hashtags_menu(post_id=payload['post_id'], message_id=message_id, page=payload.get('page', 1))
        elif payload['command'] == 'ban_user_from_suggest_post':
            self._ban_from_suggest_post(post_id=payload['post_id'], reason=payload['reason'],
                                        admin_id=admin_id, report_type=payload.get('report_type', ''))
            self._reject_post(post_id=payload['post_id'], admin_id=admin_id)
            self._update_message_post(post_id=payload['post_id'], message_id=message_id)
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
        elif payload['command'] == 'add_watermark':
            self._run_in_thread(target=self._add_watermark, args=[payload['post_id'], message_id])
        elif payload['command'] == 'reformat_text':
            _set_reformat_text(post_id=payload['post_id'])
            self._update_message_post(post_id=payload['post_id'], message_id=message_id)

    def _publish_post(self, post_id: str, admin_id: int = None, time_to_post: Optional[datetime.datetime] = None):
        post = _get_post_by_id(post_id=post_id)
        if not post:
            return

        post_params = self._get_post_params_for_publishing(post)

        try:
            if time_to_post is not None:
                post_params['publish_date'] = time_to_post.timestamp()
            new_post = self.vk_admin.wall.post(**post_params)
        except Exception as ex:
            logger.warning(f'Failed to publish post ID={post.vk_id}\n{ex}')
            return None

        new_post_id = Post.generate_id(owner_id=-self.group_id, vk_id=new_post['post_id'])

        post.suggest_status = PostStatus.POSTED.value
        if admin_id:
            post.posted_by = get_admin_by_vk_id(admin_id)
        post.is_deleted = True
        post.save()

        new_post_info = PublishedPost.create(
            suggested_post_id=post_id,
            published_post_id=new_post_id,
            admin_id=admin_id
        )

        return new_post_id

    def _update_published_post(self, post):
        post_params = self._get_post_params_for_publishing(post, with_hashtags=False)
        post_params['post_id'] = post.vk_id

        try:
            result = self.vk_admin.wall.edit(**post_params)
            return isinstance(result, dict) and result.get('post_id') == post.vk_id
        except Exception as ex:
            logger.warning(f'Failed to edit published post ID={post.vk_id}\n{ex}')
            return False

    def _get_post_params_for_publishing(self, post: Post, with_hashtags=True) -> dict:
        message = post.text

        settings = PostSettings.get_post_settings(post.id)
        if settings['reformat_text']:
            message = text_formatter.format_text(message)

        if with_hashtags:
            hashtags = [str(hashtag.hashtag) for hashtag in post.hashtags]
            if len(hashtags) > 0:
                message = message + '\n' + '\n'.join(hashtags)

        attachment = [str(attachment) for attachment in _get_post_attachments(post)]

        post_params = {
            'owner_id': -self.group_id,
            'signed': 0 if post.anonymously else 1,
            'post_id': post.vk_id,
            'message': message,
            'attachments': attachment,
        }

        return post_params

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
            self._delete_post_hashtags(post_id=post.id)

    def _add_new_message_post(self, post_id):

        post = _get_post_by_id(post_id=post_id)
        if not post:
            return

        self._update_sorted_hashtags(post)
        self._add_most_common_hashtag(post)
        self._set_anonymously_by_post_text(post)

        self.vk.messages.send(
            peer_id=self.chat_for_suggest,
            message=_get_post_description(post),
            keyboard=keyboards.main_menu_keyboard(post),
            random_id=random.randint(10 ** 5, 10 ** 6),
            attachment=[str(att) for att in _get_post_attachments(post, post.is_deleted)],
        )
        now = datetime.datetime.now()
        now = now + datetime.timedelta(microseconds=-now.microsecond)
        MessageOfSuggestedPost.create(post_id=post_id, message_date=now)

    @staticmethod
    def _add_most_common_hashtag(post: Post):
        if len(PostsHashtag.select().where(PostsHashtag.post == post)) == 0:
            hashtags = []

            minimum_number_of_characters = 15
            if config.enable_openai and len(post.text) >= minimum_number_of_characters:
                try:
                    ai_hashtags = get_hashtags.choice_hashtags_ai(post.text, get_hashtags.get_hashtags())
                except Exception as ex:
                    logger.error(f'Ошибка получения хэштегов от openai: {ex}')
                    ai_hashtags = []
                for hashtag in ai_hashtags:
                    hashtags.append(hashtag)

            if len(hashtags) == 0:
                for hashtag in SortedHashtag.select().where(SortedHashtag.post_id == post.id).limit(1):
                    if hashtag.rating is not None and hashtag.rating > 1:
                        hashtags.append(hashtag.hashtag)

            for hashtag in hashtags:
                PostsHashtag.get_or_create(post=post, hashtag=hashtag)

    def _update_message_post(self, post_id, message_id: int = None):

        post = _get_post_by_id(post_id=post_id)
        if not post:
            return
        if post.suggest_status is None or post.suggest_status == '':
            suggested_posts = Post.select().where(Post.posted_in == post).limit(1).execute()
            if len(suggested_posts) == 1:
                post = suggested_posts[0]
            else:
                return
        message_id = _get_posts_message_id(post.id, message_id)
        if not message_id:
            post_record = _get_posts_message_record(post.id)
            if not post_record:
                self._add_new_message_post(post.id)
            return

        disable_mentions = 0 if post.suggest_status == PostStatus.SUGGESTED.value else 1
        try:
            self.vk.messages.edit(
                peer_id=self.chat_for_suggest,
                conversation_message_id=message_id,
                message=_get_post_description(post),
                keyboard=keyboards.main_menu_keyboard(post),
                disable_mentions=disable_mentions,
                attachment=[str(att) for att in _get_post_attachments(post, post.is_deleted)]
            )
        except Exception as ex:
            logger.warning(f'Failed to edit message ID={message_id} for post ID={post.id}\n{ex}')

    def _show_hashtags_menu(self, post_id, message_id: int = None, page: int = 1):
        post = _get_post_by_id(post_id=post_id)
        message_id = _get_posts_message_id(post_id, message_id)
        if not post or not message_id:
            return

        text_message = _get_post_description(post=post, with_hashtags=False)
        text_message += '\nВыберите хэштеги:'
        try:
            self.vk.messages.edit(
                peer_id=self.chat_for_suggest,
                conversation_message_id=message_id,
                message=text_message,
                keyboard=keyboards.hashtag_menu(post, page),
            )
        except Exception as ex:
            logger.warning(f'Failed to edit message ID={message_id} for post ID={post_id}\n{ex}')

    def _show_conversation_menu(self, post_id, message_id: int = None, page: int = 1):
        post = _get_post_by_id(post_id=post_id)
        message_id = _get_posts_message_id(post_id, message_id)
        if not post or not message_id:
            return

        text_message = _get_post_description(post=post, with_hashtags=False)
        text_message += '\nВыберите обсуждение:'
        try:
            self.vk.messages.edit(
                peer_id=self.chat_for_suggest,
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
                                    admin=get_admin_by_vk_id(admin_id))

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
        if post.suggest_status == PostStatus.SUGGESTED.value:
            mes_text += f'\n(пост будет отклонён)'

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

        attachment = [str(attachment) for attachment in _get_post_attachments(post)]

        user_repr = 'Аноним' if post.anonymously else f'{post.user}'
        if post.user is not None and post.user.sex == 'female':
            sex_repr = 'писала'
        elif post.user is not None and post.user.sex == 'male':
            sex_repr = 'писал'
        else:
            sex_repr = 'писал(а)'
        text_message = f'{user_repr} {sex_repr}:\n{post.text}'

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

    def _add_watermark(self, post_id, message_id: int):
        post = _get_post_by_id(post_id=post_id)
        if not post:
            return
        elif not post.posted_in:
            logger.warning(f'Не пост публикации для поста из предложки {post}')
            return

        add_watermarks(post.posted_in, self.vk_admin)
        self._update_published_post(post.posted_in)
        self._update_message_post(post.id)

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

        ht_and_post = [(ht, rating, post.id) for ht, rating in get_hashtags.get_sorted_hashtags(post)]
        SortedHashtag.insert_many(ht_and_post, fields=[SortedHashtag.hashtag,
                                                       SortedHashtag.rating,
                                                       SortedHashtag.post_id]).execute()

    def _update_old_messages_of_suggested_posts(self):
        min_date = datetime.datetime.now() + datetime.timedelta(
            days=-config.days_for_checking_messages_of_suggested_posts)

        suggested_posts = Post.select(Post.id, Post.user).where(
            (Post.suggest_status == PostStatus.SUGGESTED.value) &
            (Post.is_deleted == False) &
            (Post.date >= min_date)
        ).order_by(Post.date.asc()).execute()

        td = datetime.timedelta(seconds=config.time_to_update_messages_of_suggested_posts)
        date_for_update = datetime.datetime.now() - td
        for post in suggested_posts:
            post_message_record = _get_posts_message_record(post_id=post.id)
            if post_message_record is not None and post_message_record.message_date is not None:
                if post_message_record.message_date < date_for_update:
                    self._add_new_message_post(post_id=post.id)
                    message_id = post_message_record.message_id
                    if message_id is not None:
                        try:
                            self.vk.messages.edit(
                                peer_id=config.chat_for_suggest,
                                conversation_message_id=message_id,
                                message=f'[УСТАРЕЛО]\nПост: {post} от {post.user}',
                            )
                        except Exception as ex:
                            logger.warning(f'Failed to edit message ID={message_id} for post ID={post.id}\n{ex}')
                    post_message_record.delete_instance()

    @staticmethod
    def _delete_sorted_hashtags(post_id: str):
        SortedHashtag.delete().where(SortedHashtag.post_id == post_id).execute()

    @staticmethod
    def _delete_post_hashtags(post_id: str):
        PostsHashtag.delete().where(PostsHashtag.post_id == post_id).execute()

    def _get_date_of_post_message(self, peer_id, message_id) -> Union[datetime.datetime, None]:
        mess_info = self._get_post_message_info(peer_id, message_id)
        if mess_info:
            return datetime.datetime.fromtimestamp(mess_info.get('date', 0))
        else:
            return None

    def _get_post_message_info(self, peer_id, message_id) -> Union[dict, None]:
        try:
            messages = self.vk.messages.getByConversationMessageId(
                peer_id=peer_id,
                conversation_message_ids=str(message_id)
            )
        except Exception as ex:
            logger.error(f'Can`t getByConversationMessageId peer_id={peer_id} message_id={message_id}: {ex}')
            return None
        if len(messages['items']) == 1:
            return messages['items'][0]
        elif len(messages['items']) > 1:
            logger.info(f'Too match of messages are found! peer_id={peer_id} message_id={message_id}')
        else:
            logger.info(f'Message not found! peer_id={peer_id} message_id={message_id}')

    @staticmethod
    def close_rabbit_connection():
        ConnectionsHolder.close_rabbit_connection()

    def reconnect_vk(self):
        ConnectionsHolder().vk_group_token = config.group_token_poster
        ConnectionsHolder.close_vk_connections()
        self.vk_api_admin = ConnectionsHolder().vk_api_admin
        self.vk_admin = ConnectionsHolder().vk_connection_admin
        self.vk_api_group = ConnectionsHolder().vk_api_group
        self.vk = ConnectionsHolder().vk_connection_group

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

    @staticmethod
    def _run_in_thread(target, *args, **kwargs):
        thread = threading.Thread(target=target, *args, **kwargs)
        thread.start()

    def run(self):
        if config.debug:
            self._start_polling()
        else:
            try:
                self._start_polling()
            except Exception as ex:
                self.close_rabbit_connection()
                self.reconnect_vk()
                self.reconnect_db()
                logger.error(ex)

    def run_in_loop(self):
        while True:
            self.run()
            sleep(10)


def _get_posts_message_id(post_id, message_id: int = None, show_warning=True):
    if not message_id:
        message_of_post = _get_posts_message_record(post_id)
        if message_of_post:
            message_id = message_of_post.message_id
        if message_id is None and show_warning:
            logger.warning(f'Post message information not found! Post ID={post_id}')
    return message_id


def _get_posts_message_record(post_id, message_id: Optional[int] = None, need_null_id=False) -> Union[
    MessageOfSuggestedPost, None]:
    messages_of_post = MessageOfSuggestedPost.select().where(
        (MessageOfSuggestedPost.post_id == post_id) &
        ((MessageOfSuggestedPost.message_id == message_id) if message_id is not None or need_null_id else True)
    ).order_by(
        MessageOfSuggestedPost.message_date.desc(nulls='last')).limit(1).execute()
    if len(messages_of_post) > 0:
        message_of_post = messages_of_post[0]
    else:
        message_of_post = None
    return message_of_post


def _get_post_by_id(post_id, show_warning=True) -> Union[Post, None]:
    try:
        return Post.get(id=post_id)
    except Post.DoesNotExist:
        if show_warning:
            logger.warning(f'Post not found ID={post_id}')


def _get_post_description(post: Post, with_hashtags: bool = True):
    if post.suggest_status == PostStatus.SUGGESTED.value:
        text_status = f'Новый пост {post}'
        if post.date is not None:
            delta = datetime.datetime.now() - post.date
            if delta.days == 0:
                text_status += f' ({post.date:%H:%M})'
            else:
                text_status += f'\nДата: {post.date:%Y.%m.%d %H:%M}'
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

    post_text = post.text

    settings = PostSettings.get_post_settings(post.id)
    if settings['reformat_text']:
        post_text = text_formatter.format_text(post_text)

    post_text = '[Текст отсутствует]' if post_text == '' else f'Текст поста:\n{post_text}'

    represent = f'{text_status}\n' \
                f'Автор: {post.user}\n' \
                f'{message_text}' \
                f'{post_text}\n'

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


def _get_post_attachments(post: Post, show_deleted: bool = False) -> list[UploadedFile]:
    query = PostsAttachment.select().where(
        (show_deleted | (PostsAttachment.is_deleted == False))
        & (PostsAttachment.post == post)
    ).execute()
    attachments = []
    for post_attachment in query:
        attachments.append(post_attachment.attachment)

    return attachments


def _set_reformat_text(post_id: str, value: Optional[bool] = None):
    ps, _ = PostSettings.get_or_create(post_id=post_id)
    if value is None:
        ps.reformat_text = not ps.reformat_text
    else:
        ps.reformat_text = value
    ps.save()


def add_watermarks(post: Post, vk_admin):
    logo_path = os.path.join(_current_dir(), 'logo.png')
    if not os.path.isfile(logo_path):
        logger.error(f'Не найден логотип для добавления водного знака! Путь: {logo_path}')
        return

    post_attachments = UploadedFile.select().join(
        PostsAttachment, on=(PostsAttachment.attachment == UploadedFile.id)).where(
        (UploadedFile.is_deleted == False) &
        (UploadedFile.type.in_(['photo', 'video'])) &
        (UploadedFile.is_watermarked == False) &
        (PostsAttachment.post == post) &
        (PostsAttachment.is_deleted == False)
    ).execute()

    old_attachments = []
    new_attachments = []

    for attachment in post_attachments:
        new_attachment = None
        if attachment.type == 'photo':
            new_attachment = _add_watermark_photo(attachment, logo_path, vk_admin)
        elif attachment.type == 'video':
            new_attachment = _add_watermark_video(attachment, logo_path, vk_admin)
        else:
            logger.warning(
                f'Неправильный формат типа вложения для добавления логотипа {attachment} ({attachment.type})!')
            continue

        if new_attachment is not None:
            new_attachments.append(new_attachment)
            old_attachments.append(attachment)

    for attachment in new_attachments:
        PostsAttachment.create(post=post, attachment=attachment)

    old_attachments_query = PostsAttachment.select().where(
        (PostsAttachment.post == post) &
        (PostsAttachment.attachment.in_(old_attachments)) &
        (PostsAttachment.is_deleted == False)).execute()
    for post_attachment in old_attachments_query:
        post_attachment.is_deleted = True
        post_attachment.save()
        post_attachment.attachment.is_deleted = True
        post_attachment.attachment.save()


def _add_watermark_photo(attachment: UploadedFile, logo_path: str, vk_admin):
    try:
        img_data = requests.get(attachment.url, stream=True)
    except Exception as ex:
        logger.error(f'Ошибка при загрузке изображения {attachment} {attachment.url}\n{ex}')
        img_data = None

    if img_data is not None:
        watermark = WatermarkCreator(logo_path)
        watermarked_img = watermark.add_photo_watermark(img_data)
        result_file_name = os.path.join(_current_dir(), f'{attachment}.png')
        watermarked_img.save(result_file_name)
        upload_url = vk_admin.photos.getWallUploadServer(group_id=config.group_id)['upload_url']
        result = requests.post(upload_url, files={'photo': open(result_file_name, "rb")})
        if os.path.isfile(result_file_name):
            os.remove(result_file_name)
        result_js = result.json()
        params = {'server': result_js['server'],
                  'photo': result_js['photo'],
                  'hash': result_js['hash'],
                  'group_id': config.group_id}
        # Сохраняем картинку на сервере и получаем её идентификатор
        vk_photo = vk_admin.photos.saveWallPhoto(**params)[0]
        vk_attachment = {
            'type': 'photo',
            'photo': vk_photo,
        }
        new_attachment = attachment_parser.parse_vk_attachment(vk_attachment)
        if new_attachment:
            new_attachment.is_watermarked = True
            new_attachment.save()
        return new_attachment

    else:
        return None


def _add_watermark_video(attachment: UploadedFile, logo_path: str, vk_admin):
    watermark = WatermarkCreator(logo_path)
    video_url = f'{vk_link}video{attachment.owner_id}_{attachment.vk_id}'
    try:
        video_file_name = watermark.download_video(video_url)
    except Exception as ex:
        mess_text = f'Не удалось скачать видео по ссылке {video_url} {ex}'
        logger.error(mess_text)
        try:
            vk_admin.messages.send(peer_id=config.chat_for_suggest,
                                   message=mess_text,
                                   random_id=random.randint(10 ** 5, 10 ** 6),
                                   dont_parse_links=1,
                                   )
        except Exception as ex:
            logger.error(f'Не удалось отправить сообщение об ошибке! {ex}')
        return
    new_video_file_name = watermark.add_video_watermark(video_file_name)
    if os.path.isfile(video_file_name):
        os.remove(video_file_name)
    upload_url = vk_admin.photos.getWallUploadServer(group_id=config.group_id, name=attachment.file_name)['upload_url']
    result = requests.post(upload_url, files={'video_file': open(new_video_file_name, "rb")})
    if os.path.isfile(new_video_file_name):
        os.remove(new_video_file_name)
    result_js = result.json()
    # video_id = request.json()["video_id"]
    # video_attach = 'video' + str(group_id) + '_' + str(video_id)
    # attachments.append(video_attach)

    vk_attachment = {
        'type': 'video',
        'video': result_js,
    }
    new_attachment = attachment_parser.parse_vk_attachment(vk_attachment)
    if new_attachment:
        new_attachment.is_watermarked = True
        new_attachment.save()
    return new_attachment


def _current_dir():
    return os.path.abspath(os.path.dirname(__file__))


if __name__ == '__main__':
    create_db.check_or_create_db()
    server = Server()
    server.run_in_loop()
