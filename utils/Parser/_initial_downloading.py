import datetime
import os

import config
from . import subscriptions
from . import posts
from . import users
from . import bans
from . import comments
from . import conversations
from config import logger
from Models.Users import User
from Models.Subscriptions import Subscription
from Models.Posts import Post
from Models.Conversations import Conversation
from Models.ConversationMessages import ConversationMessage
from Models.base import db
from typing import Union

_SUBS_OFFSET_FILENAME = 'current_offset_of_subscribers.tmp'
_POST_OFFSET_FILENAME = 'current_offset_of_posts.tmp'
_BAN_OFFSET_FILENAME = 'current_offset_of_bans.tmp'
_COMMENTS_OFFSET_FILENAME = 'current_offset_of_posts_for_comments.tmp'
_CONVERSATIONS_OFFSET_FILENAME = 'current_offset_of_conversations.tmp'
_CONVERSATIONS_MESS_OFFSET_FILENAME = 'current_offset_of_conversations_mess.tmp'


def load_all(vk_connection, group_id=None):
    group_id = config.group_id if group_id is None else group_id

    logger.info('Loading subscribers started')
    load_subscribers(vk_connection, group_id)
    logger.info('Loading subscribers completed')

    logger.info('Loading bans started')
    load_bans(vk_connection, group_id)
    logger.info('Loading bans completed')

    logger.info('Loading posts started')
    load_posts(vk_connection, group_id)
    logger.info('Loading posts completed')

    logger.info('Loading comments started')
    load_comments(vk_connection, group_id)
    logger.info('Loading comments completed')

    logger.info('Loading conversations started')
    load_conversations(vk_connection, group_id)
    logger.info('Loading conversations completed')

    logger.info('Loading conversations messages started')
    load_conversations_messages(vk_connection, group_id)
    logger.info('Loading conversations messages completed')

    delete_offset_files()

    logger.info('Loading completed!')


def update_subscribers(vk_connection, group_id):
    delete_offset_file(_SUBS_OFFSET_FILENAME)
    all_subscribers = _get_subscribed_users(vk_connection, group_id)
    delete_offset_file(_SUBS_OFFSET_FILENAME)

    result = {
        'subscribed': 0,
        'unsubscribed': 0,
    }

    if len(all_subscribers) == 0:
        return result

    subscribed = Subscription.get_slise_of_last(is_subscribed=True)

    now = datetime.datetime.now()
    for user in all_subscribers:
        if user not in subscribed:
            subscriptions.add_subscription(group_id=group_id,
                                           user_id=user,
                                           vk_connection=vk_connection,
                                           is_subscribed=True,
                                           subs_date=now,
                                           rewrite=True)
            logger.info(f'Добавлена подписка пользователя {user}')
            result['subscribed'] += 1

    for user in subscribed.keys():
        if user not in all_subscribers:
            subscriptions.add_subscription(group_id=group_id,
                                           user_id=user,
                                           vk_connection=vk_connection,
                                           is_subscribed=False,
                                           subs_date=now,
                                           rewrite=True)
            logger.info(f'Отписан пользователь {user}')
            result['unsubscribed'] += 1

    return result


def load_subscribers(vk_connection, group_id):
    all_subscribers = _get_subscribed_users(vk_connection, group_id)

    for user in all_subscribers:
        subscriptions.add_subscription(group_id=group_id,
                                       user_id=user,
                                       vk_connection=vk_connection,
                                       is_subscribed=True,
                                       subs_date=datetime.date(2000, 1, 1),
                                       rewrite=True)


def _get_subscribed_users(vk_connection, group_id):
    offset = get_current_offset_in_file(_SUBS_OFFSET_FILENAME)
    all_subscribers = []
    while True:
        if offset != 0:
            logger.info(f'Current subscribers offset = {offset}')
        subs = vk_connection.groups.getMembers(group_id=group_id,
                                               sort='time_asc',
                                               fields=users.users_fields(),
                                               offset=offset,
                                               count=100)['items']
        if len(subs) == 0:
            break

        with db.atomic():
            for user_info in subs:
                user = users.add_user_by_info(vk_connection, user_info)
                all_subscribers.append(user)
        offset += 100
        update_current_offset_in_file(offset, _SUBS_OFFSET_FILENAME)

    return all_subscribers


def load_posts(vk_connection, group_id):
    offset = get_current_offset_in_file(_POST_OFFSET_FILENAME)
    while True:
        if offset != 0:
            logger.info(f'Current posts offset = {offset}')
        vk_posts = vk_connection.wall.get(owner_id=-group_id,
                                          offset=offset,
                                          count=100)['items']
        if len(vk_posts) == 0:
            break
        with db.atomic():
            for vk_post in vk_posts:
                likers = vk_connection.wall.getLikes(owner_id=-group_id, post_id=vk_post['id'], count=1000)
                vk_post['likers'] = likers.get('users', [])
                post = posts.parse_wall_post(wall_post=vk_post, vk_connection=vk_connection, extract_hashtags=True)
                print(f'Post loaded {post}')

        offset += 100
        update_current_offset_in_file(offset, _POST_OFFSET_FILENAME)


def load_bans(vk_connection, group_id):
    offset = get_current_offset_in_file(_BAN_OFFSET_FILENAME)
    while True:
        if offset != 0:
            logger.info(f'Current bans offset = {offset}')
        vk_bans = vk_connection.groups.getBanned(group_id=group_id,
                                                 offset=offset,
                                                 count=100)['items']
        if len(vk_bans) == 0:
            break
        with db.atomic():
            for vk_ban in vk_bans:
                ban_info = vk_ban['ban_info']
                if 'profile' in vk_ban:
                    ban_info['user_id'] = vk_ban['profile']['id']
                    ban_info['unblock_date'] = ban_info['end_date']
                    ban = bans.parse_user_block(vk_ban=vk_ban['ban_info'], vk_connection=vk_connection)
                    print(f'Ban loaded {ban}')

        offset += 100
        update_current_offset_in_file(offset, _BAN_OFFSET_FILENAME)


def load_comments(vk_connection, group_id):
    post_offset = get_current_offset_in_file(_COMMENTS_OFFSET_FILENAME)
    if post_offset != 0:
        logger.info(f'Loading of comments started from post id={post_offset}')

    for post in Post.select().where(Post.is_deleted == False,
                                    Post.owner_id == -group_id,
                                    Post.vk_id > post_offset).order_by(Post.vk_id):
        post_comments = comments.load_post_comments(post, vk_connection, group_id)

        if len(post_comments) > 0:
            print(f'Loaded {len(post_comments)} comments for {post}')
            update_current_offset_in_file(post.vk_id, _COMMENTS_OFFSET_FILENAME)


def load_conversations(vk_connection, group_id):
    offset = get_current_offset_in_file(_CONVERSATIONS_OFFSET_FILENAME)
    while True:
        if offset != 0:
            logger.info(f'Current conversations offset = {offset}')
        topics = vk_connection.board.getTopics(
            group_id=group_id_without_minus(group_id),
            offset=offset,
            count=100,
            preview=1
        )['items']
        if len(topics) == 0:
            break

        with db.atomic():
            for topic in topics:
                conversation = conversations.parse_conversation(vk_object=topic,
                                                                vk_connection=vk_connection,
                                                                owner_id=group_id_with_minus(group_id))

                print(f'Сonversation loaded {conversation.get_url()}')

        offset += 100
        update_current_offset_in_file(offset, _CONVERSATIONS_OFFSET_FILENAME)


def update_conversations_messages(vk_connection, group_id):
    delete_offset_file(_CONVERSATIONS_MESS_OFFSET_FILENAME)
    messages = load_conversations_messages(vk_connection, group_id)
    delete_offset_file(_CONVERSATIONS_MESS_OFFSET_FILENAME)

    deleted_messages = ConversationMessage.select().where(
        (ConversationMessage.id.not_in(messages)) &
        (ConversationMessage.is_deleted == False)
    ).execute()

    for message in deleted_messages:
        message.is_deleted = True
        message.save()
        logger.info(f'Сообщение {message} помечено как удаленное')


def load_conversations_messages(vk_connection, group_id):
    conv_offset = get_current_offset_in_file(_CONVERSATIONS_MESS_OFFSET_FILENAME)
    if conv_offset != 0:
        logger.info(f'Loading of conversations comments started from conv id={conv_offset}')
    messages = []
    count_for_get = 100  # min = 10, max = 100
    for conv in Conversation.select().where(
            Conversation.is_deleted == False,
            Conversation.owner_id == group_id_with_minus(group_id),
            Conversation.conversation_id > conv_offset).order_by(Conversation.conversation_id):
        offset = 0
        count = 0
        params = {
            'group_id': group_id_without_minus(group_id),
            'topic_id': conv.conversation_id,
            'need_likes': 0,
            'count': count_for_get,
            'sort': 'asc',
            'extended': 1,
        }
        while True:
            with db.atomic():
                vk_comments = vk_connection.board.getComments(offset=offset, **params)
                for user_info in vk_comments['profiles']:
                    user = users.add_user_by_info(vk_connection, user_info)
                for vk_comment in vk_comments['items']:
                    comment = conversations.parse_conversation_message(vk_comment,
                                                                       vk_connection,
                                                                       conversation=conv)
                    messages.append(comment)
                    count += 1
            offset += count_for_get
            if len(vk_comments['items']) < count_for_get:
                break

        if count > 0:
            print(f'Loaded {count} comments for conversation {conv.get_url()}')
            update_current_offset_in_file(conv.conversation_id, _CONVERSATIONS_MESS_OFFSET_FILENAME)
    return messages


def update_current_offset_in_file(offset, temp_file_name):
    with open(temp_file_name, 'w') as tmp_file:
        tmp_file.write(str(offset))
        tmp_file.close()


def get_current_offset_in_file(temp_file_name):
    offset = 0
    try:
        with open(temp_file_name, 'r') as tmp_file:
            str_offset = tmp_file.read()
            offset = 0 if str_offset == '' else int(str_offset)
            tmp_file.close()
    except FileNotFoundError:
        pass
    return offset


def delete_offset_files():
    delete_offset_file(_SUBS_OFFSET_FILENAME)
    delete_offset_file(_POST_OFFSET_FILENAME)
    delete_offset_file(_COMMENTS_OFFSET_FILENAME)
    delete_offset_file(_CONVERSATIONS_OFFSET_FILENAME)
    delete_offset_file(_CONVERSATIONS_MESS_OFFSET_FILENAME)
    delete_offset_file(_BAN_OFFSET_FILENAME)


def delete_offset_file(file_name):
    if os.path.exists(file_name):
        try:
            os.remove(file_name)
        except Exception as ex:
            logger.error(f'Can`t remove offset file: {ex}')


def group_id_with_minus(group_id: Union[int, str]) -> int:
    int_group_id = 0
    if isinstance(group_id, str):
        if len(group_id) > 0:
            int_group_id = int(group_id)
    else:
        int_group_id = group_id
    if int_group_id > 0:
        int_group_id = - int_group_id
    return int_group_id


def group_id_without_minus(group_id: Union[int, str]) -> int:
    int_group_id = 0
    if isinstance(group_id, str):
        if len(group_id) > 0:
            int_group_id = int(group_id)
    else:
        int_group_id = group_id
    if int_group_id < 0:
        int_group_id = - int_group_id
    return int_group_id
