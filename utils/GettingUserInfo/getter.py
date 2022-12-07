import config
from Models.Comments import Comment
from Models.ChatMessages import ChatMessage
from Models.Users import User
from Models.Admins import Admin, get_admin_by_vk_id
from Models.BanedUsers import BanedUser, BAN_REASONS
from Models.Posts import Post, PostStatus
from Models.Relations import PostsLike, CommentsLike, PostsAttachment
from Models.Relations import CommentsAttachment, ConversationsMessageAttachment, ChatMessageAttachment
from Models.UploadedFiles import UploadedFile
from Models.Subscriptions import Subscription
from config import logger
from utils.db_helper import queri_to_list
import datetime
import random
from typing import Union, Optional
from . import keyboards, querys

MAX_MESSAGE_SIZE = 4048


def parse_event(event, vk_connection, vk_connection_admin=None):
    user = None
    if ('payload' in event.object
            and event.object.payload.get('command').startswith('show_ui')):
        user_id = event.object.payload.get('user_id')
    else:
        return

    user = get_user_from_message(str(user_id))
    if user is None:
        return

    payload = event.object.payload
    command = payload.get('command')

    if command == 'show_ui_published_posts':

        posts = querys.users_posts(user=user, published=True)

        if len(posts) > 0:
            post = posts[0]
            show_post_info(event, vk_connection, post, published=True)

    elif command == 'show_ui_unpublished_posts':

        posts = querys.users_posts(user=user, published=False)

        if len(posts) > 0:
            post = posts[0]

            show_post_info(event, vk_connection, post, published=False)

    elif command == 'show_ui_show_post':
        post_id = payload.get('post_id')
        published = payload.get('published', True)
        try:
            post = Post.get(id=post_id)
        except Post.DoesNotExist:
            logger.warning(f'Can`t find post by id={post_id}')
            return
        show_post_info(event, vk_connection, post, published)

    elif command == 'show_ui_comments':
        page = payload.get('page', 0)
        show_comments(event, vk_connection, user, page)

    elif command == 'show_ui_conv_messages':
        page = payload.get('page', 0)
        show_conv_messages(event, vk_connection, user, page)

    elif command == 'show_ui_chat_messages':
        page = payload.get('page', 0)
        show_chat_messages(event, vk_connection, user, page)

    elif command == 'show_ui_user_ban_menu':
        show_ban_menu(event, vk_connection, user)

    elif command == 'show_ui_ban_user':

        if vk_connection_admin:
            _ban_user_from_info_message(event, vk_connection_admin, user, payload)
        show_ban_menu(event, vk_connection, user)

    elif command == 'show_ui_delete_all_comments':

        if vk_connection_admin:
            _delete_all_comments(vk_connection_admin, user)
        show_main_user_info_menu(event, vk_connection, user)

    else:

        show_main_user_info_menu(event, vk_connection, user)


def show_main_user_info_menu(event, vk_connection, user):
    try:
        result = vk_connection.messages.edit(peer_id=event.object.peer_id,
                                             conversation_message_id=event.object.conversation_message_id,
                                             message=get_short_user_info(user),
                                             keyboard=keyboards.main_menu_keyboard(user=user))
    except Exception as ex:
        logger.warning(f'Failed to edit message ID={event.object.conversation_message_id}\n{ex}')


def show_post_info(event, vk_connection, post, published=True):
    attachments = PostsAttachment.select().where((PostsAttachment.post == post)
                                                 & (PostsAttachment.is_deleted == False)).join(UploadedFile)
    attachments_list = []
    for attachment in attachments:
        attachments_list.append(f'{attachment.attachment}_{attachment.attachment.access_key}')

    post_description = _get_post_description(post)

    try:
        result = vk_connection.messages.edit(peer_id=event.object.peer_id,
                                             conversation_message_id=event.object.conversation_message_id,
                                             message=post_description,
                                             attachments=attachments_list,
                                             keyboard=keyboards.post_menu(user=post.user,
                                                                          current_post_id=post.id,
                                                                          published=published))
    except Exception as ex:
        logger.warning(f'Failed to edit message ID={event.object.conversation_message_id}\n{ex}')


def show_ban_menu(event, vk_connection, user: User):
    mes_text = f'Выберите причину блокировки пользователя {user}'

    try:
        result = vk_connection.messages.edit(peer_id=event.object.peer_id,
                                             conversation_message_id=event.object.conversation_message_id,
                                             message=mes_text,
                                             keyboard=keyboards.user_ban_menu(user=user))
    except Exception as ex:
        logger.warning(f'Failed to edit message ID={event.object.conversation_message_id}\n{ex}')


def _get_post_description(post: Post):
    post_repr = f'{post} от {post.date:%Y.%m.%d %H:%M}'

    represent = f'{post_repr}\n' \
                f'Текст поста:\n' \
                f'{post.text}\n'

    if post.attachments:
        represent += f'\nВложений: {len(post.attachments)}'

    if post.likes:
        represent += f'\nЛайков: {len(post.likes)}'

    if post.comments:
        represent += f'\nКомментариев: {len(post.comments)}'

    if len(represent) > MAX_MESSAGE_SIZE:
        represent_without_text = represent.replace(post.text, '')
        represent = represent.replace(
            post.text,
            post.text[:(MAX_MESSAGE_SIZE - len(represent_without_text) - 3)] + '...'
        )

    return represent


def show_comments(event, vk_connection, user, page):
    try:
        result = vk_connection.messages.edit(peer_id=event.object.peer_id,
                                             conversation_message_id=event.object.conversation_message_id,
                                             message=get_comments_from_page(user, page),
                                             keyboard=keyboards.comments_menu(user=user,
                                                                              current_page=page))
    except Exception as ex:
        logger.warning(f'Failed to edit message ID={event.object.conversation_message_id}\n{ex}')


def get_comments_from_page(user: User, page=0):
    comments_per_page = 6
    splitter = '\n\n'
    max_comment_size = int(MAX_MESSAGE_SIZE / comments_per_page - len(splitter))
    comments_pages = querys.comments_by_pages(user, comments_per_page)
    if len(comments_pages) == 0:
        return f'Не найдены комментарии пользователя {user}'

    page_number = min(len(comments_pages) - 1, page)

    comments_descriptions = []
    for comment in comments_pages[page_number]:
        descr = f'Комментарий от {comment.date:%Y.%m.%d}\n' \
                f'{comment.get_url()}\n' \
                f'{comment.text}\n' \
                f'Вложений:{len(comment.attachments)}; Лайков: {len(comment.likes)}'
        if len(descr) >= max_comment_size:
            descr_without_text = descr.replace(comment.text, '')
            descr = descr.replace(
                comment.text,
                comment.text[:(max_comment_size - len(descr_without_text) - 3)] + '...'
            )
        comments_descriptions.append(descr)

    return splitter.join(comments_descriptions)


def show_conv_messages(event, vk_connection, user, page):
    try:
        result = vk_connection.messages.edit(peer_id=event.object.peer_id,
                                             conversation_message_id=event.object.conversation_message_id,
                                             message=get_conv_messages_from_page(user, page),
                                             keyboard=keyboards.conv_messages_menu(user=user,
                                                                                   current_page=page))
    except Exception as ex:
        logger.warning(f'Failed to edit message ID={event.object.conversation_message_id}\n{ex}')


def get_conv_messages_from_page(user: User, page=0):
    messages_per_page = 6
    splitter = '\n\n'
    max_conv_message_size = int(MAX_MESSAGE_SIZE / messages_per_page - len(splitter))
    conv_messages = querys.conv_messages_by_pages(user, count=messages_per_page)
    if len(conv_messages) == 0:
        return f'Не найдены сообщения в обсуждениях пользователя {user}'

    page_number = min(len(conv_messages) - 1, page)

    conv_messages_descriptions = []
    for message in conv_messages[page_number]:
        descr = _chat_message_description(message)
        if len(descr) >= max_conv_message_size:
            descr_without_text = descr.replace(message.text, '')
            descr = descr.replace(
                message.text,
                message.text[:(max_conv_message_size - len(descr_without_text) - 3)] + '...'
            )
        conv_messages_descriptions.append(descr)

    return splitter.join(conv_messages_descriptions)


def _chat_message_description(message):
    conversation = message.conversation
    conversation_text = '' if conversation is None else f'{conversation.title} {conversation.get_url()}\n'
    del_text = '[DELETED] ' if message.is_deleted else ''
    descr = f'Сообщение от {message.date:%Y.%m.%d}\n' \
            f'{conversation_text}' \
            f'{del_text}{message.get_url()}\n' \
            f'{message.text}\n' \
            f'Вложений:{len(message.attachments)}'
    return descr


def show_chat_messages(event, vk_connection, user, page):
    try:
        result = vk_connection.messages.edit(peer_id=event.object.peer_id,
                                             conversation_message_id=event.object.conversation_message_id,
                                             message=get_chat_messages_from_page(user, page),
                                             keyboard=keyboards.chat_messages_menu(user=user,
                                                                                   current_page=page))
    except Exception as ex:
        logger.warning(f'Failed to edit message ID={event.object.conversation_message_id}\n{ex}')


def get_chat_messages_from_page(user: User, page=0):
    messages_per_page = 6
    splitter = '\n\n'
    max_chat_message_size = int(MAX_MESSAGE_SIZE / messages_per_page - len(splitter))
    chat_messages = querys.chat_messages_by_pages(user, messages_per_page)
    if len(chat_messages) == 0:
        return f'Не найдены сообщения в чатах пользователя {user}'

    page_number = min(len(chat_messages) - 1, page)

    chat_messages_descriptions = []
    for message in chat_messages[page_number]:
        chat_text = '' if message.chat is None else f'{message.chat}\n'
        descr = f'Сообщение от {message.date:%Y.%m.%d}\n' \
                f'в чате {chat_text}' \
                f'{message.text}\n' \
                f'Вложений:{len(message.attachments)}'
        if len(descr) >= max_chat_message_size:
            descr_without_text = descr.replace(message.text, '')
            descr = descr.replace(
                message.text,
                message.text[:(max_chat_message_size - len(descr_without_text) - 3)] + '...'
            )
        chat_messages_descriptions.append(descr)

    return splitter.join(chat_messages_descriptions)


def send_user_info(user, vk_connection, peer_id: int):
    short_user_info = get_short_user_info(user)
    try:
        message_id = vk_connection.messages.send(peer_id=peer_id,
                                                 message=short_user_info,
                                                 keyboard=keyboards.main_menu_keyboard(user=user),
                                                 random_id=random.randint(10 ** 5, 10 ** 6))
    except Exception as ex:
        logger.warning(f'Failed send message peer_id={peer_id}\n{ex}')


def get_user_from_message(message_text: str):
    user_str = message_text

    user_str = user_str.replace('https://vk.com/', '')

    if user_str.startswith('id'):
        user_str = user_str.replace('id', '')

    if user_str.isdigit():
        try:
            user = User.get(id=int(user_str))
            return user
        except User.DoesNotExist:
            pass
    else:
        try:
            user = User.get(domain=user_str)
            return user
        except User.DoesNotExist:
            pass

    return None


def get_short_user_info(user: User):
    subscribe_history = Subscription.select().where(Subscription.user == user).order_by(Subscription.date)
    subscribe_history_list = []
    for subscribe in subscribe_history:
        state = 'ПОДПИСАН' if subscribe.is_subscribed else 'ОТПИСАН'
        if subscribe.date is None:
            date_sub = '<Неизвестно когда>'
        elif subscribe.date == datetime.datetime(2000, 1, 1):
            date_sub = 'Давно'
        else:
            date_sub = f'{subscribe.date:%Y-%m-%d}'
        subscribe_history_list.append(f'{date_sub} {state}')

    bun_record = None
    bun_records = BanedUser.select().where(BanedUser.user == user).order_by(BanedUser.date.desc()).execute()
    if len(bun_records):
        bun_record = bun_records[0]

    mes_text = f'Информация о пользователе {user} (id {user.id}):\n'
    mes_text += f'Упоминания в ВК: https://vk.com/feed?obj={user.id}&q=&section=mentions\n'

    if user.comment is not None and user.comment != '':
        mes_text += f'ВНИМАНИЕ: {user.comment}\n'

    if bun_record:
        reason_str = BAN_REASONS.get(bun_record.reason, 'просто так')
        admin_str = f' админом {bun_record.admin}' if bun_record.admin else ''
        date_from_str = ' давно' if bun_record.date is None else f' {bun_record.date:%Y-%m-%d}'
        date_to_str = ' навсегда' if bun_record.unblock_date is None else f' до {bun_record.unblock_date:%Y-%m-%d}'
        mes_text += f'\nЗАБАНЕН{admin_str}{date_from_str}{date_to_str} за {reason_str}\n'

    if len(subscribe_history_list) == 0:
        mes_text += '\nПОЛЬЗОВАТЕЛЬ НЕ ПОДПИСАН!'
    else:
        mes_text += '\nИстория подписок: \n' + '\n'.join(subscribe_history_list) + '\n'
    published_posts = Post.select().where((Post.user == user)
                                          & (Post.suggest_status.is_null())).order_by(Post.date.desc()).limit(3)
    published_posts_list = []
    for users_post in published_posts:
        published_posts_list.append(f'{users_post} от {users_post.date:%Y-%m-%d}')
    if len(published_posts_list) > 0:
        mes_text += '\nПоследние опубликованные посты:\n' + '\n'.join(published_posts_list) + '\n'

    non_published_posts = Post.select().where((Post.user == user)
                                              & ((Post.suggest_status == PostStatus.REJECTED.value) |
                                                 (Post.suggest_status == PostStatus.SUGGESTED.value))
                                              ).order_by(Post.date.desc()).limit(3)
    non_published_posts_list = []
    for users_post in non_published_posts:
        non_published_posts_list.append(f'{users_post} от {users_post.date:%Y-%m-%d}')
    if len(non_published_posts_list) > 0:
        mes_text += '\nПоследние неопубликованные посты:\n' + '\n'.join(non_published_posts_list) + '\n'

    count_of_comments = len(user.comments)
    if count_of_comments > 0:
        mes_text += f'\nНаписал комментариев: {count_of_comments}\n'

    count_of_posts_likes = len(PostsLike.select().where(PostsLike.user == user))
    count_of_self_posts_likes = len(
        PostsLike.select().join(Post).where(
            (PostsLike.user == user) & (PostsLike.liked_object.user == user)))
    if count_of_posts_likes > 0:
        mes_text += f'\nЛайкнул постов: {count_of_posts_likes}'
        mes_text += '\n' if count_of_self_posts_likes == 0 else f' (в т.ч. своих: {count_of_self_posts_likes})\n'

    count_of_comments_likes = len(CommentsLike.select().where(CommentsLike.user == user))
    count_of_self_com_likes = len(
        CommentsLike.select().join(Comment).where(
            (CommentsLike.user == user) & (CommentsLike.liked_object.user == user)))
    if count_of_comments_likes > 0:
        mes_text += f'\nЛайкнул комментариев: {count_of_comments_likes}'
        mes_text += '\n' if count_of_self_com_likes == 0 else f' (в т.ч. своих: {count_of_self_com_likes})\n'

    return mes_text


def _ban_user_from_info_message(event, vk_connection_admin, user, payload: dict):
    admin_id = event.object.get('user_id')
    admin = None if admin_id is None else get_admin_by_vk_id(admin_id)

    report_type = payload.get('report_type', '')
    comment = 'по результатам анализа информации о пользователе' if report_type == '' else ''
    ban_user_with_report(vk_connection_admin=vk_connection_admin,
                         user=user,
                         reason=payload.get('reason', 0),
                         report_type=report_type,
                         comment=comment,
                         admin=get_admin_by_vk_id(admin_id))


def ban_user_with_report(vk_connection_admin, user: User, reason: int, report_type='', comment='',
                         admin: Optional[Admin] = None, end_date=0, comment_visible=0) -> Union[BanedUser, None]:
    banned = _ban_user(vk_connection_admin, user, reason, comment, end_date, comment_visible)

    if banned:
        if report_type != '':
            _report_user(vk_connection_admin, user, report_type, comment)

        new_record, _ = BanedUser.get_or_create(user=user)
        new_record.user = user
        new_record.date = datetime.datetime.now()
        new_record.reason = reason
        new_record.admin = admin
        new_record.report_type = report_type
        new_record.comment = comment
        new_record.save()

        return new_record


def _ban_user(vk_connection_admin, user: User, reason: int, comment='', end_date=0, comment_visible=0):
    banned = False
    try:
        result = vk_connection_admin.groups.ban(group_id=config.group_id,
                                                owner_id=user.id,
                                                end_date=end_date,
                                                reason=reason,
                                                comment=comment,
                                                comment_visible=comment_visible,
                                                )
        if result:
            banned = True
            logger.info(f'Пользователь {user} забанен')
    except Exception as ex:
        logger.warning(f'Failed to ban user {user}\n{ex}')

    return banned


def _report_user(vk_connection_admin, user: User, report_type, comment=''):
    reported = False
    if config.debug:
        logger.warning('Предотвращена попытка отправки жалобы при отладке!')
        return reported

    try:
        result = vk_connection_admin.users.report(user_id=user.id,
                                                  type=report_type,
                                                  comment=comment,
                                                  )
        if result:
            reported = True
            logger.info(f'Отправлена жалоба на пользователя {user}')
    except Exception as ex:
        logger.warning(f'Failed to report user {user}\n{ex}')

    return reported


def _delete_all_comments(vk_connection_admin, user: User):
    for comment in Comment.select().where((Comment.user == user) & (Comment.is_deleted == False)):
        try:
            result = vk_connection_admin.wall.deleteComment(owner_id=comment.owner_id,
                                                            comment_id=comment.vk_id)
        except Exception as ex:
            logger.error(f'Не удалось удалить комментарий {comment} {ex}')
            result = None

        if result == 1:
            comment.is_deleted = True
            comment.save()
