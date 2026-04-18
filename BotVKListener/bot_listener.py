import datetime
import os
import random
import threading
import time
from time import sleep

import requests
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

import config as config
from ChatBot.chat_bot import ChatBot
from Models import create_db
from Models.Admins import Admin
from Models.ChatMessages import ChatMessage
from Models.Chats import Chat
from Models.Comments import Comment
from Models.ConversationMessages import ConversationMessage
from Models.Posts import Post, PostStatus
from Models.PrivateMessages import PrivateMessage
from Models.Relations import PostsLike, CommentsLike
from Models.Subscriptions import Subscription
from Models.Users import User
from Models.base import db
from Models.create_db import check_and_create_db
from Models.db_transfer import export_models
from config import logger
from utils import regvk
from utils.GettingUserInfo.getter import get_user_from_message, send_user_info, parse_event
from utils.Parser import _initial_downloading, subscriptions, private_messages
from utils.Parser import chats, conversations, comments, likes, posts, bans
from utils.connection_holder import ConnectionsHolder
from utils.db_helper import queri_to_list
from utils.rabbit_connector import send_message, get_messages


class Server:
    vk_link = 'https://vk.ru/'

    def __init__(self):
        self.group_id = config.group_id
        self.chat_bot = ChatBot()

        self.chat_for_suggest = config.chat_for_suggest

        self._check_token_on_startup()
        self.vk_api_admin = ConnectionsHolder().vk_api_admin
        self.vk_connection_admin = ConnectionsHolder().vk_connection_admin
        self.vk_api_group = ConnectionsHolder().vk_api_group
        self.vk_connection_group = ConnectionsHolder().vk_connection_group

        self._updated_reg_dates = []

    def _start_polling(self):
        self._longpoll = VkBotLongPoll(self.vk_api_group, self.group_id, wait=5)

        logger.info('Bot listener started!')

        time_to_update_last_posts = 60*60
        last_published_posts_update = None
        time_to_update_last_chat_messages = 20
        last_chat_messages_update = None
        time_to_healthcheck = config.healthcheck_interval / 4
        last_healthcheck = None
        token_check_interval = 5  # Интервал проверки токена
        last_token_check = None

        while True:

            # Проверяем токен с заданной периодичностью
            now = datetime.datetime.now()
            if not last_token_check or (now - last_token_check).total_seconds() >= token_check_interval:
                self._check_token_and_reconnect_if_needed()
                last_token_check = now

            for event in self._longpoll.check():
                new_object = None
                if config.debug:
                    logger.info(f'New event: {event.type}')
                if event.type == VkBotEventType.WALL_POST_NEW:
                    new_object = posts.parse_wall_post(event.object, self.vk_connection_admin)
                    self._process_new_post_event(new_post=new_object)
                elif event.type == 'like_add':
                    new_object = likes.parse_like_add(event.object, self.vk_connection_admin)
                elif event.type == 'like_remove':
                    likes.parse_like_remove(event.object, self.vk_connection_admin)
                elif event.type == VkBotEventType.WALL_REPLY_NEW:
                    new_object = comments.parse_comment(event.object, self.vk_connection_admin)
                    if new_object is not None:
                        send_message('new_comments', str(new_object.id))
                elif event.type == VkBotEventType.WALL_REPLY_DELETE:
                    comments.parse_delete_comment(event.object, self.vk_connection_admin)
                elif event.type == VkBotEventType.WALL_REPLY_RESTORE:
                    comments.parse_restore_comment(event.object, self.vk_connection_admin)
                elif event.type == VkBotEventType.GROUP_JOIN:
                    new_object = subscriptions.parse_subscription(event, self.vk_connection_admin, True)
                elif event.type == VkBotEventType.GROUP_LEAVE:
                    new_object = subscriptions.parse_subscription(event, self.vk_connection_admin, False)
                elif event.type == VkBotEventType.BOARD_POST_NEW:
                    new_object = conversations.parse_conversation_message(event.object, self.vk_connection_admin)
                    if new_object is not None:
                        send_message('new_conversation_message', str(new_object.id))
                elif event.type == VkBotEventType.BOARD_POST_EDIT:
                    conversations.parse_conversation_message(event.object, self.vk_connection_admin, is_edited=True)
                elif event.type == VkBotEventType.BOARD_POST_DELETE:
                    conversations.parse_delete_conversation_message(event.object)
                elif event.type == VkBotEventType.BOARD_POST_RESTORE:
                    conversations.parse_undelete_conversation_message(event.object)
                elif event.type == VkBotEventType.MESSAGE_NEW:
                    if event.from_chat and str(event.object['message']['peer_id']) == str(self.chat_for_suggest):
                        if 'load_data' in event.object.message['text']:
                            words = event.object.message['text'].split()
                            if len(words) == 1:
                                _initial_downloading.load_all(
                                    vk_connection=self.vk_connection_admin,
                                    vk_connection_grope=self.vk_connection_group)
                            elif len(words) == 2 and words[1].isdigit():
                                group_id = int(event.object.message['text'].split()[1])
                                _initial_downloading.load_all(
                                    vk_connection=self.vk_connection_admin,
                                    group_id=group_id,
                                    vk_connection_grope=self.vk_connection_group)
                        if event.object.message['text'] == 'create_db':
                            db.close()
                            sleep(1)
                            create_db.create_all_tables()
                        elif event.object.message['text'] == 'recreate_db':
                            sleep(5)
                            db.close()
                            sleep(5)
                            create_db.recreate_database()
                        elif event.object.message['text'] == 'lock_db':
                            create_db.lock_db()
                        elif event.object.message['text'] == 'unlock_db':
                            create_db.unlock_db()
                        if 'load_bans' in event.object.message['text']:
                            words = event.object.message['text'].split()
                            if len(words) == 1:
                                _initial_downloading.load_bans(self.vk_connection_admin, self.group_id)
                            elif len(words) == 2 and words[1].isdigit():
                                group_id = int(event.object.message['text'].split()[1])
                                _initial_downloading.load_bans(self.vk_connection_admin, group_id)
                    else:
                        if PrivateMessage.it_is_private_chat(event.object.message.get('peer_id')):
                            if self._user_is_admin(event.object.message.get('peer_id')):
                                self._process_admin_chat_event(event)
                            else:
                                new_object = private_messages.parse_private_message(event.object.message,
                                                                                    self.vk_connection_admin)
                                send_message(message_type='new_private_message', message=new_object.id)
                            self.chat_bot.chat(event)
                        else:
                            new_object = chats.parse_chat_message(vk_object=event.object.message,
                                                                  vk_connection=self.vk_connection_admin,
                                                                  owner_id=-event.group_id)
                            if new_object:
                                send_message(message_type='new_chat_message', message=new_object.id)

                elif event.type == VkBotEventType.MESSAGE_REPLY:
                    if PrivateMessage.it_is_private_chat(event.object.get('peer_id')):
                        if event.from_user:
                            new_object = private_messages.parse_private_message(event.object,
                                                                                self.vk_connection_admin)
                            send_message(message_type='new_private_message', message=new_object.id)
                elif event.type == VkBotEventType.MESSAGE_EVENT:
                    if ('payload' in event.object
                            and event.object.payload.get('command', '').startswith('show_ui')):
                        parse_event(event=event, vk_connection=self.vk_connection_group,
                                    vk_connection_admin=self.vk_connection_admin)
                elif event.type == VkBotEventType.USER_BLOCK:
                    bans.parse_user_block(event.object, self.vk_connection_admin)
                elif event.type == VkBotEventType.USER_UNBLOCK:
                    bans.parse_user_unblock(event.object, self.vk_connection_admin)

                if new_object:
                    self._run_in_thread(target=self._update_user_reg_dates_in_new_object,
                                        args=[new_object])

            now = datetime.datetime.now()
            if not last_published_posts_update \
                    or (now - last_published_posts_update).total_seconds() >= time_to_update_last_posts:
                try:
                    self._run_in_thread(target=self._update_last_posts)
                    # self._update_last_posts()
                except Exception as ex:
                    logger.error(f'Failed to update last posts: {ex}')
                last_published_posts_update = datetime.datetime.now()

            now = datetime.datetime.now()
            if not last_chat_messages_update \
                    or (now - last_chat_messages_update).total_seconds() >= time_to_update_last_chat_messages:
                try:
                    self._run_in_thread(target=self._update_last_chat_messages)
                    # self._update_last_chat_messages()
                except Exception as ex:
                    logger.error(f'Failed to update last chat messages: {ex}')
                last_chat_messages_update = datetime.datetime.now()

            now = datetime.datetime.now()
            if not last_healthcheck or (now - last_healthcheck).total_seconds() >= time_to_healthcheck:
                self._run_in_thread(target=self._answer_healthcheck_messages)
                last_healthcheck = datetime.datetime.now()

    def _check_token_on_startup(self):
        """Проверяет наличие и валидность токена при запуске бота"""
        try:
            from Models.AppTokens import AppToken

            token_record = AppToken.get_master_token()

            if not token_record:
                logger.error("=" * 60)
                logger.error("❌ НЕТ ТОКЕНА АДМИНИСТРАТОРА!")
                logger.error("=" * 60)
                logger.error("Для работы бота необходимо добавить в .env файл:")
                logger.error("  ADMIN_ACCESS_TOKEN=ваш_токен")
                logger.error("  ADMIN_REFRESH_TOKEN=ваш_refresh_токен (опционально)")
                logger.error("  ADMIN_TOKEN_EXPIRES_AT=2024-01-01T00:00:00 (опционально)")
                logger.error("=" * 60)

                # Отправляем сообщение в healthcheck-чат если возможно
                message = '❌ Бот запущен без токена администратора!\n\n' \
                          'Добавьте ADMIN_ACCESS_TOKEN в .env файл и перезапустите бота.'
                try:
                    if self.vk_connection_group:
                        self.vk_connection_group.messages.send(
                            peer_id=config.healthcheck_chat_id,
                            message=message,
                            random_id=random.randint(10 ** 5, 10 ** 6)
                        )
                except:
                    logger.error(message)
                return

            if token_record.is_expired(buffer_minutes=0):
                logger.warning(f"⚠️ Токен администратора ИСТЁК! Действителен был до: {token_record.expires_at}")
                logger.warning("Обновите ADMIN_ACCESS_TOKEN в .env файле")
            else:
                expires_in = token_record.seconds_until_expiry()
                logger.info(f"✅ Токен администратора валиден. Истекает через {expires_in / 3600:.1f} часов")

        except Exception as ex:
            logger.error(f"Error checking token on startup: {ex}")

    def _check_token_on_startup(self):
        """Проверяет наличие и валидность токена при запуске бота"""
        try:
            from Models.AppTokens import AppToken

            token_record = AppToken.get_master_token()

            if not token_record:
                logger.error("=" * 60)
                logger.error("❌ НЕТ ТОКЕНА АДМИНИСТРАТОРА!")
                logger.error("=" * 60)
                logger.error("Для работы бота необходимо добавить в .env файл:")
                logger.error("  ADMIN_ACCESS_TOKEN=ваш_токен")
                logger.error("  ADMIN_REFRESH_TOKEN=ваш_refresh_токен (опционально)")
                logger.error("  ADMIN_TOKEN_EXPIRES_AT=2024-01-01T00:00:00 (опционально)")
                logger.error("=" * 60)

                # Отправляем сообщение в healthcheck-чат если возможно
                try:
                    if self.vk_connection_group:
                        self.vk_connection_group.messages.send(
                            peer_id=config.healthcheck_chat_id,
                            message='❌ Бот запущен без токена администратора!\n\n'
                                    'Добавьте ADMIN_ACCESS_TOKEN в .env файл и перезапустите бота.',
                            random_id=random.randint(10 ** 5, 10 ** 6)
                        )
                except:
                    pass
                return

            if token_record.is_expired(buffer_minutes=0):
                logger.warning(f"⚠️ Токен администратора ИСТЁК! Действителен был до: {token_record.expires_at}")
                logger.warning("Обновите ADMIN_ACCESS_TOKEN в .env файле")
            else:
                expires_in = token_record.seconds_until_expiry()
                logger.info(f"✅ Токен администратора валиден. Истекает через {expires_in / 3600:.1f} часов")

        except Exception as ex:
            logger.error(f"Error checking token on startup: {ex}")

    def _check_token_and_reconnect_if_needed(self):
        """Проверяет токен и переподключается при необходимости"""
        try:
            from Models.AppTokens import AppToken
            token_record = AppToken.get_master_token()

            if not token_record:
                return

            # Если токен истёк или истекает менее чем через 30 секунд
            if token_record.is_expired() or token_record.seconds_until_expiry() < 30:
                config.logger.warning(
                    f"Token is expiring soon ({token_record.seconds_until_expiry():.0f}s). Waiting for refresh...")

                # Ждём до 60 секунд, пока шедуллер обновит токен
                for _ in range(60):
                    time.sleep(1)
                    token_record = AppToken.get_master_token()
                    if token_record and not token_record.is_expired() and token_record.seconds_until_expiry() > 60:
                        # Токен обновлён
                        config.logger.info("Token has been refreshed. Reconnecting...")
                        self._reconnect_admin_api()
                        return True
                    elif token_record and token_record.seconds_until_expiry() > 10:
                        # Ещё есть время
                        continue

                # Если за 60 секунд не обновилось
                self._send_healthcheck_alert("Токен не обновлён более 60 секунд!")
                return False

        except Exception as ex:
            config.logger.error(f"Error checking token: {ex}")

        return True

    def _reconnect_admin_api(self):
        """Переподключает API админа с новым токеном"""
        from utils.connection_holder import ConnectionsHolder

        # Сбрасываем соединение в ConnectionHolder
        holder = ConnectionsHolder()
        holder._vk_api_admin = None
        holder._vk_connection_admin = None

        # Обновляем локальные ссылки
        self.vk_api_admin = holder.vk_api_admin
        self.vk_connection_admin = holder.vk_connection_admin

        config.logger.info("Admin API reconnected successfully")

    def _send_healthcheck_alert(self, message):
        """Отправляет сообщение в чат healthcheck"""
        try:
            if self.vk_connection_group:
                self.vk_connection_group.messages.send(
                    peer_id=config.healthcheck_chat_id,
                    message=f'🚨 {message}\n\nБот может работать некорректно. Проверьте токен администратора.',
                    random_id=random.randint(10 ** 5, 10 ** 6)
                )
        except Exception as ex:
            config.logger.error(f"Failed to send healthcheck alert: {ex}")

    @staticmethod
    def _run_in_thread(target, *args, **kwargs):
        thread = threading.Thread(target=target, *args, **kwargs)
        thread.start()

    @staticmethod
    def _answer_healthcheck_messages():
        message_type = f'{config.healthcheck_queue_name_prefix}_listener_requests'
        messages = get_messages(message_type=message_type)
        answer_message_type = f'{config.healthcheck_queue_name_prefix}_listener_answers'
        for message_text in messages:
            send_message(message_type=answer_message_type, message=message_text)

    def _update_last_posts(self, count_of_posts: int = 60):
        days_for_update = 14

        date_to_start = datetime.datetime.now() - datetime.timedelta(days=days_for_update)
        last_posts = Post.select().where((Post.date > date_to_start)
                                         & ((Post.suggest_status.is_null())
                                            | (Post.suggest_status == PostStatus.SUGGESTED.value))
                                         ).order_by(Post.date.desc()).limit(count_of_posts)
        last_posts_list = queri_to_list(last_posts, 'id')
        if len(last_posts_list) > 0:
            posts_info = self.vk_connection_admin.wall.getById(posts=', '.join(last_posts_list))
            for post_info in posts_info:
                post, was_updated = posts.update_wall_post(post_info, self.vk_connection_admin)
                if was_updated:
                    send_message('updated_posts', post.id)
                    comments.mark_posts_comments_as_deleted(post=post, is_deleted=post.is_deleted)

    def _update_last_chat_messages(self):
        for chat in Chat.select():
            messages = ChatMessage.select().where(ChatMessage.chat == chat).order_by(ChatMessage.date.desc()).limit(50)
            ids = [str(mes.message_id) for mes in messages]
            if len(ids) == 0:
                continue
            messages_info = self.vk_connection_admin.messages.getByConversationMessageId(
                peer_id=str(chat.chat_id),
                conversation_message_ids=', '.join(ids),
                group_id=str(config.group_id),
            )
            for mess_info in messages_info.get('items', []):
                message, updated = chats.update_chat_message(vk_object=mess_info,
                                                             vk_connection=self.vk_connection_admin,
                                                             owner_id=-config.group_id)
                if updated:
                    send_message(message_type='updated_chat_message', message=message.id)

    def _process_admin_chat_event(self, event):
        message_text = event.object.message.get('text', '')
        if message_text.startswith('disable_keyboard'):
            words = message_text.split()
            if len(words) == 2:
                peer_id = words[1]
                self._disable_keyboard(peer_id)
        elif message_text == 'update_subscribers':
            self._run_in_thread(target=self._update_subscribers, args=[event.object.message['peer_id']])
        elif message_text == 'update_conversations_messages':
            self._send_from_group(peer_id=event.object.message.get('peer_id'),
                                  message=f'Начато обновление сообщений в обсуждениях')
            self._run_in_thread(target=_initial_downloading.update_conversations_messages,
                                args=[self.vk_connection_admin, config.group_id])
        elif message_text == 'backup_db':
            self._send_from_group(event.object.message.get('peer_id'), f'Бэкап формируется, ждите...')
            self._run_in_thread(target=self._send_backup, args=[event.object.message.get('peer_id')])

        user = get_user_from_message(message_text)
        if user is not None:
            send_user_info(user=user,
                           vk_connection=self.vk_connection_group,
                           peer_id=event.object.message.get('peer_id'))
        if posts.it_is_post_url(message_text):
            self._run_in_thread(
                target=self._update_post_info,
                args=[message_text, event.object.message.get('peer_id')]
            )

    def _disable_keyboard(self, peer_id):
        try:
            self.vk_connection_group.messages.send(peer_id=int(peer_id),
                                                   message='Клавиатура отключена',
                                                   keyboard='{"one_time":true,"inline":false,"buttons":[]}',
                                                   random_id=random.randint(10 ** 5, 10 ** 6))
        except Exception as ex:
            logger.info(f'Failed disable keyboard in chat peer_id={peer_id}:\n{ex}')

    def _update_post_info(self, url, report_peer_id=None):
        post, created, updated = posts.parse_post_by_url(
            url=url,
            vk_connection=self.vk_connection_admin
        )
        if created:
            self._process_new_post_event(new_post=post)
            text_status = 'загружен'
        elif updated:
            text_status = 'обновлен'
        else:
            text_status = 'не изменен'

        if post.suggest_status is None:
            loaded_comments = comments.load_post_comments(post, self.vk_connection_admin)
            comments_status = f' Найдено комментариев: {len(loaded_comments)}.'
        else:
            comments_status = ''

        if report_peer_id:
            self.vk_connection_group.messages.send(
                peer_id=report_peer_id,
                message=f'Пост {post} от {post.user} {text_status}.{comments_status}',
                random_id=random.randint(10 ** 5, 10 ** 6))

        if not created:
            send_message('updated_posts', post.id)

    @staticmethod
    def _process_new_post_event(new_post):
        str_from_user = '' if new_post.user is None else f'от {new_post.user} '
        str_attachments = '' if len(
            new_post.attachments) == 0 else f', вложений: {len(new_post.attachments)}'
        str_action = 'Post published' if new_post.suggest_status is None else 'Suggested new post'
        logger.info(f'{str_action} {str_from_user}{new_post}{str_attachments}')

        if new_post.suggest_status == PostStatus.SUGGESTED.value:
            send_message(message_type='new_suggested_post', message=new_post.id)
        elif new_post.suggest_status is None:
            send_message(message_type='new_posted_post', message=new_post.id)

    def _send_backup(self, peer_id):
        zip_path = ''
        try:
            # 1. Создаём бэкап
            zip_path = export_models(create_db.all_models())

            # 2. Получаем URL для загрузки
            upload_info = self.vk_connection_group.docs.getMessagesUploadServer(peer_id=peer_id)
            upload_url = upload_info['upload_url']

            # 3. Загружаем файл через POST-запрос
            with open(zip_path, 'rb') as f:
                response = requests.post(upload_url, files={'file': f})
            response.raise_for_status()

            upload_data = response.json()

            # 4. Сохраняем документ на сервере VK
            save_result = self.vk_connection_group.docs.save(
                file=upload_data['file'],
                title=os.path.basename(zip_path)
            )

            # 5. Получаем attachment
            doc = save_result['doc'] if 'doc' in save_result else save_result[0]['doc']
            attachment = f"doc{doc['owner_id']}_{doc['id']}"

            # 6. Отправляем сообщение в чат
            self._send_from_group(
                peer_id=peer_id,
                message="📦 Бэкап базы данных успешно создан и прикреплён ниже.",
                attachment=attachment)
            logger.info(f'The backup was sent successfully.')

        except Exception as ex:
            logger.error(f'Failed to send backup {zip_path}: {ex}')
            self._send_from_group(peer_id, f"⚠️ Ошибка при создании бэкапа: {ex}")

        finally:
            # Чистим временный файл
            try:
                if os.path.exists(zip_path):
                    os.remove(zip_path)
            except Exception as ex:
                logger.error(f'Error deleting temporary file {zip_path}: {ex}')

    def _update_subscribers(self, peer_id=None):
        if peer_id:
            self._send_from_group(peer_id, f'Начато обновление состава подписчиков...')
        result = _initial_downloading.update_subscribers(self.vk_connection_admin,
                                                         config.group_id,
                                                         self.vk_connection_group)
        if peer_id:
            self._send_from_group(peer_id, f'Обновление состава подписчиков завершено.'
                                           f'\nПодписано: {result["subscribed"]}'
                                           f'\nОтписано: {result["unsubscribed"]}')

        if peer_id:
            self._send_from_group(peer_id, f'Начато обновление дат регистрации пользователей...')
        result = _update_user_reg_dates()
        if peer_id:
            self._send_from_group(peer_id, f'Обновлено {result} дат регистрации пользователей.')

    def _update_user_reg_dates_in_new_object(self, vk_object):
        """
        Обновляет дату регистрации пользователя из события, если она не заполнена
        Проверенные пользователи складываются в _updated_reg_dates чтобы не получать их данные
        """
        # Проверяем, есть ли у этого события пользователь
        if isinstance(vk_object,
                      (Comment, ConversationMessage, Post, ChatMessage,
                       Subscription, CommentsLike, PostsLike, PrivateMessage)):

            user = vk_object.user

            if user and user not in self._updated_reg_dates and user.registration_date is None:
                _update_user_reg_date(user)
                self._updated_reg_dates.append(user)

    def _send_from_group(self, peer_id, message, attachment=None, keyboard=None):
        try:
            return self.vk_connection_group.messages.send(
                peer_id=peer_id,
                random_id=random.randint(10 ** 5, 10 ** 6),
                message=message,
                attachment=attachment,
                keyboard=keyboard,
            )
        except Exception as ex:
            logger.error(f'Error sending message: {ex}')

    @staticmethod
    def _user_is_admin(user_id):
        admins = Admin.select().join(User).where(User.id == user_id).limit(1)
        return len(admins) > 0

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


def _update_user_reg_dates():
    """
    Обновляет даты регистрации всех пользователей, у кого они не заполнены
    """
    count = 0

    users = User.select().where(User.registration_date.is_null())
    for user in users:

        if user.id <= 0:
            continue

        delay_before = random.randint(100, 500)  # 100-500 мс
        time.sleep(delay_before / 1000)

        if _update_user_reg_date(user):
            count += 1

        delay_after = random.randint(100, 500)  # 100-500 мс
        time.sleep(delay_after / 1000)

    return count


def _update_user_reg_date(user: User):
    """
    Обновляет дату регистрации пользователя
    """
    if user.id > 0 and user.registration_date is None:
        try:
            registration_date = regvk.get_registration_date(user.id)
            if registration_date:
                user.registration_date = registration_date
                user.save()
                return True
        except Exception as ex:
            logger.error(ex)
    return False


if __name__ == '__main__':
    check_and_create_db()
    server = Server()
    server.run_in_loop()
