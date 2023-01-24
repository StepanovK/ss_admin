import config as config
from config import logger
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from time import sleep
import datetime
import pika
from Models.base import db
from Models.Chats import Chat
from Models.ChatMessages import ChatMessage
from Models.Posts import Post, PostStatus
from Models.PrivateMessages import PrivateMessage
from Models.Admins import Admin
from Models.Users import User
from Models import create_db
from utils.db_helper import queri_to_list
from utils.connection_holder import ConnectionsHolder
from utils.rabbit_connector import send_message, send_message_by_chanel, get_messages_from_chanel
from utils.GettingUserInfo.getter import get_user_from_message, send_user_info, parse_event
from ChatBot.chat_bot import ChatBot
from utils.Parser import _initial_downloading, subscriptions, private_messages
from utils.Parser import chats, conversations, comments, likes, posts, bans
import random
import threading


class Server:
    vk_link = 'https://vk.com/'

    def __init__(self):
        self.group_id = config.group_id
        self.chat_bot = ChatBot()

        self.chat_for_suggest = config.chat_for_suggest

        self.vk_api_admin = ConnectionsHolder().vk_api_admin
        self.vk_connection_admin = ConnectionsHolder().vk_connection_admin
        self.vk_api_group = ConnectionsHolder().vk_api_group
        self.vk_connection_group = ConnectionsHolder().vk_connection_group

    def _start_polling(self):
        self._longpoll = VkBotLongPoll(self.vk_api_group, self.group_id, wait=5)

        logger.info('Bot listener started!')

        time_to_update_last_posts = 20
        last_published_posts_update = None
        time_to_update_last_chat_messages = 20
        last_chat_messages_update = None

        while True:
            for event in self._longpoll.check():
                if config.debug:
                    logger.info(f'New event: {event.type}')
                if event.type == VkBotEventType.WALL_POST_NEW:
                    new_post = posts.parse_wall_post(event.object, self.vk_connection_admin)
                    self._process_new_post_event(new_post=new_post)
                elif event.type == 'like_add':
                    likes.parse_like_add(event.object, self.vk_connection_admin)
                elif event.type == 'like_remove':
                    likes.parse_like_remove(event.object, self.vk_connection_admin)
                elif event.type == VkBotEventType.WALL_REPLY_NEW:
                    comment = comments.parse_comment(event.object, self.vk_connection_admin)
                    if comment is not None:
                        send_message('new_comments', str(comment.id))
                elif event.type == VkBotEventType.WALL_REPLY_DELETE:
                    comments.parse_delete_comment(event.object, self.vk_connection_admin)
                elif event.type == VkBotEventType.WALL_REPLY_RESTORE:
                    comments.parse_restore_comment(event.object, self.vk_connection_admin)
                elif event.type == VkBotEventType.GROUP_JOIN:
                    subscriptions.parse_subscription(event, self.vk_connection_admin, True)
                elif event.type == VkBotEventType.GROUP_LEAVE:
                    subscriptions.parse_subscription(event, self.vk_connection_admin, False)
                elif event.type == VkBotEventType.BOARD_POST_NEW:
                    conv_mes = conversations.parse_conversation_message(event.object, self.vk_connection_admin)
                    if conv_mes is not None:
                        send_message('new_conversation_message', str(conv_mes.id))
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
                                message = private_messages.parse_private_message(event.object.message,
                                                                                 self.vk_connection_admin)
                                send_message(message_type='new_private_message', message=message.id)
                            self.chat_bot.chat(event)
                        else:
                            message = chats.parse_chat_message(vk_object=event.object.message,
                                                               vk_connection=self.vk_connection_admin,
                                                               owner_id=-event.group_id)
                            if message:
                                send_message(message_type='new_chat_message', message=message.id)

                elif event.type == VkBotEventType.MESSAGE_REPLY:
                    if PrivateMessage.it_is_private_chat(event.object.get('peer_id')):
                        if event.from_user:
                            message = private_messages.parse_private_message(event.object,
                                                                             self.vk_connection_admin)
                            send_message(message_type='new_private_message', message=message.id)
                elif event.type == VkBotEventType.MESSAGE_EVENT:
                    if ('payload' in event.object
                            and event.object.payload.get('command', '').startswith('show_ui')):
                        parse_event(event=event, vk_connection=self.vk_connection_group,
                                    vk_connection_admin=self.vk_connection_admin)
                elif event.type == VkBotEventType.USER_BLOCK:
                    bans.parse_user_block(event.object, self.vk_connection_admin)
                elif event.type == VkBotEventType.USER_UNBLOCK:
                    bans.parse_user_unblock(event.object, self.vk_connection_admin)

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

            self._run_in_thread(target=self._answer_healthcheck_messages)
            # self._answer_healthcheck_messages()

    @staticmethod
    def _run_in_thread(target, *args, **kwargs):
        thread = threading.Thread(target=target, *args, **kwargs)
        thread.start()

    @staticmethod
    def _answer_healthcheck_messages():
        rabbit_connection = ConnectionsHolder().rabbit_connection
        if rabbit_connection:
            channel = rabbit_connection.channel()
            messages = get_messages_from_chanel(
                message_type=f'{config.healthcheck_queue_name_prefix}_listener_requests',
                channel=channel)
            for message_text in messages:
                send_message_by_chanel(message_type=f'{config.healthcheck_queue_name_prefix}_listener_answers',
                                       message=message_text, channel=channel)
            ConnectionsHolder().close_rabbit_connection()
        else:
            logger.warning(f'Failed connect to rabbit!')

    def _update_last_posts(self, count_of_posts: int = 60):
        days_for_update = 14

        date_to_start = datetime.datetime.now() - datetime.timedelta(days=days_for_update)
        last_posts = Post.select().where((Post.date > date_to_start)
                                         & ((Post.suggest_status.is_null())
                                            | (Post.suggest_status == PostStatus.SUGGESTED.value))
                                         ).order_by(Post.date.desc()).limit(count_of_posts)
        last_posts_list = queri_to_list(last_posts, 'id')
        if len(last_posts_list) > 0:
            # print(f'updating posts: {last_posts_list}')
            posts_info = self.vk_connection_admin.wall.getById(posts=', '.join(last_posts_list))
            for post_info in posts_info:
                post, was_updated = posts.update_wall_post(post_info, self.vk_connection_admin)
                if was_updated:
                    send_message('updated_posts', post.id)
                    comments.mark_posts_comments_as_deleted(post=post, is_deleted=post.is_deleted)
                # print(f'post {post} was_updated={was_updated}')

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
                try:
                    self.vk_connection_group.messages.send(peer_id=int(peer_id),
                                                           message='Клавиатура отключена',
                                                           keyboard='{"one_time":true,"inline":false,"buttons":[]}',
                                                           random_id=random.randint(10 ** 5, 10 ** 6))
                except Exception as ex:
                    logger.info(f'Failed disable keyboard in chat peer_id={peer_id}:\n{ex}')

        user = get_user_from_message(message_text)
        if user is not None:
            send_user_info(user=user,
                           vk_connection=self.vk_connection_group,
                           peer_id=event.object.message.get('peer_id'))
        if posts.it_is_post_url(message_text):
            post, created, updated = posts.parse_post_by_url(
                url=message_text,
                vk_connection=self.vk_connection_admin
            )
            if created:
                self._process_new_post_event(new_post=post)
                text_status = 'загружен'
            elif updated:
                text_status = 'обновлен'
            else:
                text_status = 'не изменен'

            self.vk_connection_group.messages.send(
                peer_id=event.object.message.get('peer_id'),
                message=f'Пост {post} от {post.user} {text_status}',
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


if __name__ == '__main__':
    server = Server()
    server.run_in_loop()
