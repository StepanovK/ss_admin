from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from Models.Posts import Post, PostStatus
from Models.Users import User
from Models.BanedUsers import BanedUser, BAN_REASONS, REPORT_TYPES_BY_BAN_REASONS
from Models.Comments import Comment
from Models.ConversationMessages import ConversationMessage
from Models.ChatMessages import ChatMessage
from . import querys
from utils.db_helper import queri_to_list


def main_menu_keyboard(user: User):
    keyboard = VkKeyboard(one_time=False, inline=True)

    published_posts = querys.users_posts(user=user, published=True)
    need_new_line = False
    if len(published_posts) > 0:
        if need_new_line:
            keyboard.add_line()
        keyboard.add_callback_button(label=f'Опубликованные посты ({len(published_posts)})',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": "show_ui_published_posts", "user_id": user.id})
        need_new_line = True

    unpublished_posts = querys.users_posts(user=user, published=False)
    if len(unpublished_posts) > 0:
        if need_new_line:
            keyboard.add_line()
        keyboard.add_callback_button(label=f'Неопубликованные посты ({len(unpublished_posts)})',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": "show_ui_unpublished_posts", "user_id": user.id})
        need_new_line = True

    comments = querys.users_comments(user=user)
    if len(comments) > 0:
        if need_new_line:
            keyboard.add_line()
        keyboard.add_callback_button(label=f'Комментарии к постам ({len(comments)})',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": "show_ui_comments", "user_id": user.id})
        need_new_line = True

    conv_mes = querys.users_conv_messages(user=user)
    if len(conv_mes) > 0:
        if need_new_line:
            keyboard.add_line()
        keyboard.add_callback_button(label=f'Сообщения в обсуждениях ({len(conv_mes)})',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": "show_ui_conv_messages", "user_id": user.id})
        need_new_line = True

    chat_mess = querys.users_chat_messages(user=user)
    if len(chat_mess) > 0:
        if need_new_line:
            keyboard.add_line()
        keyboard.add_callback_button(label=f'Сообщения в чатах ({len(chat_mess)})',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": "show_ui_chat_messages", "user_id": user.id})
        need_new_line = True

    if need_new_line:
        keyboard.add_line()
    keyboard.add_callback_button(label='Обновить',
                                 color=VkKeyboardColor.PRIMARY,
                                 payload={"command": "show_ui_user_short_info", "user_id": user.id})
    keyboard.add_callback_button(label='ЗАБАНИТЬ',
                                 color=VkKeyboardColor.NEGATIVE,
                                 payload={"command": "show_ui_user_ban_menu", "user_id": user.id})
    if user_is_banned(user) and user_has_comments(user):
        keyboard.add_callback_button(label='Удалить все комментарии',
                                     color=VkKeyboardColor.NEGATIVE,
                                     payload={"command": "show_ui_delete_all_comments", "user_id": user.id})

    return keyboard.get_keyboard()


def post_menu(user: User, published: bool = True, current_post_id=None):
    posts = querys.users_posts(user=user, published=published)
    previous_post = None
    this_post_position = 0
    next_post = None
    for i in range(len(posts)):
        if current_post_id is not None and posts[i].id == current_post_id:
            this_post_position = i
            if i != 0:
                previous_post = posts[i - 1]
            if i < (len(posts) - 1):
                next_post = posts[i + 1]

    keyboard = VkKeyboard(one_time=False, inline=True)

    need_line = False

    if previous_post is not None:
        keyboard.add_callback_button(label=f'< Предыдущий ({this_post_position})',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": "show_ui_show_post",
                                              "user_id": user.id,
                                              "post_id": previous_post.id,
                                              "published": published})
        need_line = True

    if next_post is not None:
        keyboard.add_callback_button(label=f'Следующий ({len(posts) - this_post_position - 1}) >',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": "show_ui_show_post",
                                              "user_id": user.id,
                                              "post_id": next_post.id,
                                              "published": published})

        need_line = True

    if need_line:
        keyboard.add_line()

    if previous_post is not None:
        keyboard.add_callback_button(label=f'<< Первый',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": "show_ui_show_post",
                                              "user_id": user.id,
                                              "post_id": posts[0].id,
                                              "published": published})
        need_line = True

    if next_post is not None:
        keyboard.add_callback_button(label=f'Последний >>',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": "show_ui_show_post",
                                              "user_id": user.id,
                                              "post_id": posts[-1].id,
                                              "published": published})
        need_line = True

    if need_line:
        keyboard.add_line()

    keyboard.add_callback_button(label='На главную',
                                 color=VkKeyboardColor.PRIMARY,
                                 payload={"command": "show_ui_user_short_info", "user_id": user.id})

    return keyboard.get_keyboard()


def comments_menu(user: User, current_page=0):
    return page_menu(user=user,
                     command="show_ui_comments",
                     pages=querys.comments_by_pages(user, count=6),
                     current_page=current_page)


def conv_messages_menu(user: User, current_page=0):
    return page_menu(user=user,
                     command="show_ui_conv_messages",
                     pages=querys.conv_messages_by_pages(user),
                     current_page=current_page)


def chat_messages_menu(user: User, current_page=0):
    return page_menu(user=user,
                     command="show_ui_chat_messages",
                     pages=querys.chat_messages_by_pages(user),
                     current_page=current_page)


def page_menu(user: User, command, pages: list, current_page=0, count_per_page=6):
    previous_page = None if current_page == 0 else current_page - 1
    next_page = None if len(pages) <= (current_page + 1) else current_page + 1

    keyboard = VkKeyboard(one_time=False, inline=True)

    need_line = False

    if previous_page is not None:
        keyboard.add_callback_button(label=f'< Предыдущая ({current_page})',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": command,
                                              "user_id": user.id,
                                              "page": previous_page})
        need_line = True

    if next_page is not None:
        count = (len(pages) - current_page - 1)
        keyboard.add_callback_button(label=f'Следующая ({count}) >',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": command,
                                              "user_id": user.id,
                                              "page": next_page})

        need_line = True

    if need_line:
        keyboard.add_line()

    if previous_page is not None:
        keyboard.add_callback_button(label=f'<< Первая',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": command,
                                              "user_id": user.id,
                                              "page": 0})
        need_line = True

    if next_page is not None:
        keyboard.add_callback_button(label=f'Последняя >>',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": command,
                                              "user_id": user.id,
                                              "page": len(pages) - 1})
        need_line = True

    if need_line:
        keyboard.add_line()

    keyboard.add_callback_button(label='На главную',
                                 color=VkKeyboardColor.PRIMARY,
                                 payload={"command": "show_ui_user_short_info", "user_id": user.id})

    return keyboard.get_keyboard()


def user_ban_menu(user: User):
    keyboard = VkKeyboard(one_time=False, inline=True)

    keyboard.add_callback_button(label='<< Назад',
                                 color=VkKeyboardColor.PRIMARY,
                                 payload={"command": "show_ui_user_short_info", "user_id": user.id})

    payload = {"command": "show_ui_ban_user", "user_id": user.id}
    add_ban_buttons(keyboard=keyboard, user=user, payload=payload)

    return keyboard.get_keyboard()


def add_ban_buttons(keyboard: VkKeyboard, user: User, payload: dict):
    user_bans = BanedUser.select().where(BanedUser.user == user).execute()

    for reason, reason_name in BAN_REASONS.items():
        keyboard.add_line()

        color_ban = VkKeyboardColor.SECONDARY
        color_report = VkKeyboardColor.SECONDARY
        report_type = REPORT_TYPES_BY_BAN_REASONS.get(reason)

        for user_ban in user_bans:
            if user_ban.reason == reason:
                color_ban = VkKeyboardColor.PRIMARY
                if user_ban.report_type != '' and user_ban.report_type == report_type:
                    color_report = VkKeyboardColor.PRIMARY
                break

        ban_payload = payload.copy()
        ban_payload['reason'] = reason
        keyboard.add_callback_button(label=reason_name.capitalize(),
                                     color=color_ban,
                                     payload=ban_payload)

        if report_type:
            report_payload = ban_payload.copy()
            report_payload['report_type'] = report_type
            keyboard.add_callback_button(label='с жалобой',
                                         color=color_report,
                                         payload=report_payload)


def user_is_banned(user):
    try:
        BanedUser.get(user=user)
        return True
    except BanedUser.DoesNotExist:
        return False


def user_has_comments(user):
    user_comment = Comment.select().where(
        (Comment.user == user) & (Comment.is_deleted == False)).limit(1).execute()
    return len(user_comment) != 0
