from vk_api.keyboard import VkKeyboard, VkKeyboardButton, VkKeyboardColor
from Models.Posts import Post, PostStatus, PostsHashtag
from BotVKPoster.PosterModels.SortedHashtags import SortedHashtag
import utils.config as config
from utils.db_helper import queri_to_list
import collections


def main_menu_keyboard(post: Post):
    keyboard = VkKeyboard(one_time=False, inline=True)

    if post.suggest_status == PostStatus.SUGGESTED.value:
        keyboard.add_callback_button(label='Опубликовать',
                                     color=VkKeyboardColor.PRIMARY,
                                     payload={"command": "public_post", "post_id": post.id})
        keyboard.add_line()
        keyboard.add_callback_button(label='Редактировать хэштеги',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": "edit_hashtags", "post_id": post.id, 'page': 1})
        keyboard.add_line()

    keyboard.add_callback_button(label='Информация о пользователе',
                                 color=VkKeyboardColor.SECONDARY,
                                 payload={"command": "show_user_info", "post_id": post.id})

    if post.suggest_status == PostStatus.SUGGESTED.value:
        keyboard.add_line()
        keyboard.add_callback_button(label='Отклонить',
                                     color=VkKeyboardColor.NEGATIVE,
                                     payload={"command": "reject", "post_id": post.id})

    return keyboard.get_keyboard()


def hashtag_menu(post: Post, page: int = 1):
    keyboard = VkKeyboard(one_time=False, inline=True)

    keyboard.add_callback_button(label='Закончить',
                                 color=VkKeyboardColor.POSITIVE,
                                 payload={"command": "show_main_menu", "post_id": post.id})

    added_hashtags = queri_to_list(post.hashtags)
    hashtags_pages = _hashtags_by_pages(post)
    page = min(max(hashtags_pages.keys()), page)
    current_page_hashtags = hashtags_pages[page]

    for ht in current_page_hashtags:
        keyboard.add_line()
        if ht in added_hashtags:
            command = 'remove_hashtag'
            color = VkKeyboardColor.PRIMARY
        else:
            command = 'add_hashtag'
            color = VkKeyboardColor.SECONDARY
        keyboard.add_callback_button(label=ht,
                                     color=color,
                                     payload={"command": command, "post_id": post.id, 'hashtag': ht, 'page': page})

    next_page_hashtags = hashtags_pages[(page + 1)]
    next_page_exists = len(next_page_hashtags) > 0

    if page > 1 or next_page_exists:
        keyboard.add_line()

    if page > 1:
        keyboard.add_callback_button(label='<< Назад',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": "edit_hashtags", "post_id": post.id, 'page': page - 1})

    if next_page_exists:
        keyboard.add_callback_button(label='Далее >>',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": "edit_hashtags", "post_id": post.id, 'page': page + 1})

    return keyboard.get_keyboard()


def user_info_menu(post: Post, page: int = 1):
    keyboard = VkKeyboard(one_time=False, inline=True)

    keyboard.add_callback_button(label='<< Назад',
                                 color=VkKeyboardColor.SECONDARY,
                                 payload={"command": "show_main_menu", "post_id": post.id})

    return keyboard.get_keyboard()


def _hashtags_by_pages(post: Post) -> dict[list]:
    count_per_page = 4
    sorted_hashtags = queri_to_list(SortedHashtag.select().where(SortedHashtag.post_id == post.id), column='hashtag')
    for ht in config.hashtags:
        if ht not in sorted_hashtags:
            sorted_hashtags.append(ht)

    pages = collections.defaultdict(list)

    current_page = 1
    current_count = 0
    for ht in sorted_hashtags:
        if current_count < count_per_page:
            pages[current_page].append(ht)
            current_count += 1
        else:
            current_count = 0
            current_page += 1

    return pages
