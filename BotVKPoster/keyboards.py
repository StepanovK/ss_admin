import functools
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from Models.Posts import Post, PostStatus
from Models.Conversations import Conversation
from Models.ConversationMessages import ConversationMessage
from PosterModels.SortedHashtags import SortedHashtag
import config as config
from utils.db_helper import queri_to_list
import collections
from utils.get_hasgtags import get_hashtags, get_sorted_hashtags
from peewee import fn, JOIN


def main_menu_keyboard(post: Post):
    keyboard = VkKeyboard(one_time=False, inline=True)

    can_edit = post.suggest_status == PostStatus.SUGGESTED.value and not post.is_deleted

    if can_edit:
        keyboard.add_callback_button(label='Опубликовать',
                                     color=VkKeyboardColor.POSITIVE,
                                     payload={"command": "publish_post", "post_id": post.id})
        if post.anonymously:
            keyboard.add_callback_button(label='&#9989; анонимно',
                                         color=VkKeyboardColor.PRIMARY,
                                         payload={"command": "set_anonymously", "post_id": post.id, 'val': False})
        else:
            keyboard.add_callback_button(label='&#9725; анонимно',
                                         color=VkKeyboardColor.SECONDARY,
                                         payload={"command": "set_anonymously", "post_id": post.id, 'val': True})
        keyboard.add_line()
        keyboard.add_callback_button(label='# Редактировать хэштеги',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": "edit_hashtags", "post_id": post.id, 'page': 1})
        keyboard.add_line()

    keyboard.add_callback_button(label='&#128214; Информация о пользователе',
                                 color=VkKeyboardColor.SECONDARY,
                                 payload={"command": "show_user_info", "post_id": post.id})

    keyboard.add_line()
    keyboard.add_callback_button(label='Переслать в обсуждение',
                                 color=VkKeyboardColor.SECONDARY,
                                 payload={"command": "show_conversation_menu", "post_id": post.id, 'page': 1})

    if can_edit:
        keyboard.add_line()
        keyboard.add_callback_button(label='&#128259; Обновить информацию',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": "update_post", "post_id": post.id})
        keyboard.add_line()
        keyboard.add_callback_button(label='Отклонить',
                                     color=VkKeyboardColor.NEGATIVE,
                                     payload={"command": "reject_post", "post_id": post.id})

    return keyboard.get_keyboard()


def hashtag_menu(post: Post, page: int = 1):
    keyboard = VkKeyboard(one_time=False, inline=True)

    keyboard.add_callback_button(label='Закончить',
                                 color=VkKeyboardColor.POSITIVE,
                                 payload={"command": "show_main_menu", "post_id": post.id})

    keyboard.add_callback_button(label='Закончить и опубликовать',
                                 color=VkKeyboardColor.POSITIVE,
                                 payload={"command": "publish_post", "post_id": post.id})

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

    # next_page_hashtags = hashtags_pages[(page + 1)]
    next_page_exists = len(hashtags_pages) > page

    if page > 1 or next_page_exists:
        keyboard.add_line()

    if page > 1:
        keyboard.add_callback_button(label=f'<< Назад ({page - 1})',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": "edit_hashtags", "post_id": post.id, 'page': page - 1})

    if next_page_exists:
        keyboard.add_callback_button(label=f'Далее ({len(hashtags_pages) - page}) >>',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": "edit_hashtags", "post_id": post.id, 'page': page + 1})

    return keyboard.get_keyboard()


def user_info_menu(post: Post, page: int = 1):
    keyboard = VkKeyboard(one_time=False, inline=True)

    keyboard.add_callback_button(label='<< Назад',
                                 color=VkKeyboardColor.SECONDARY,
                                 payload={"command": "show_main_menu", "post_id": post.id})

    return keyboard.get_keyboard()


def conversation_menu(post: Post, page: int = 1):
    keyboard = VkKeyboard(one_time=False, inline=True)

    keyboard.add_callback_button(label='<< Вернуться в главное меню',
                                 color=VkKeyboardColor.SECONDARY,
                                 payload={"command": "show_main_menu", "post_id": post.id})

    conversations_of_post = Conversation.select().join(
        ConversationMessage).where(
        (ConversationMessage.from_post == post) &
        (ConversationMessage.is_deleted == False)).distinct().execute()

    pages = _conversations_by_pages(post)
    page = min(max(pages.keys()), page)
    current_page = pages[page]

    for conversation in current_page:
        keyboard.add_line()
        if conversation in conversations_of_post.row_cache:
            color = VkKeyboardColor.PRIMARY
        else:
            color = VkKeyboardColor.SECONDARY
        keyboard.add_callback_button(
            label=str(conversation)[:50],
            color=color,
            payload={
                "command": 'post_to_conversation',
                "post_id": post.id,
                'conversation': conversation.id,
                'page': page})

    next_page_exists = len(pages) > page
    if page > 1 or next_page_exists:
        keyboard.add_line()

    if page > 1:
        keyboard.add_callback_button(
            label=f'<< Назад ({page - 1})',
            color=VkKeyboardColor.SECONDARY,
            payload={"command": "show_conversation_menu", "post_id": post.id, 'page': page - 1})

    if next_page_exists:
        keyboard.add_callback_button(
            label=f'Далее ({len(pages) - page}) >>',
            color=VkKeyboardColor.SECONDARY,
            payload={"command": "show_conversation_menu", "post_id": post.id, 'page': page + 1})

    return keyboard.get_keyboard()


@functools.lru_cache()
def _hashtags_by_pages(post: Post) -> dict[int, list]:
    count_per_page = 4
    sorted_hashtags = queri_to_list(SortedHashtag.select().where(SortedHashtag.post_id == post.id), column='hashtag')
    for ht in get_hashtags():
        if ht not in sorted_hashtags:
            sorted_hashtags.append(ht)

    pages = collections.defaultdict(list)

    current_page = 1
    current_count = 0
    for ht in sorted_hashtags:
        if current_count >= count_per_page:
            current_count = 0
            current_page += 1
        pages[current_page].append(ht)
        current_count += 1

    return pages


@functools.lru_cache()
def _conversations_by_pages(post: Post):
    count_messages = ConversationMessage.select(
        ConversationMessage.conversation,
        fn.Count(ConversationMessage.id).alias('count_messages')
    ).where(
        (ConversationMessage.is_deleted == False)
    ).join(Post).group_by(ConversationMessage.conversation)

    conversations_query = Conversation.select(
        Conversation, count_messages.c.count_messages
    ).join(count_messages,
           JOIN.LEFT_OUTER,
           on=(count_messages.c.conversation_id == Conversation.id)
           ).order_by(count_messages.c.count_messages.desc(nulls='last'))

    pages = collections.defaultdict(list)

    for i in range(1, 100):
        res = conversations_query.paginate(i, paginate_by=4).execute()
        if len(res) == 0:
            break
        page = []
        for conv in res:
            page.append(conv)
        pages[i] = page

    return pages


if __name__ == '__main__':
    _conversations_by_pages(None)
