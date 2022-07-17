from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from Models.Posts import Post, PostStatus
from Models.Users import User
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
