import functools
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from Models.Posts import Post, PostStatus, PostsHashtag
from Models.Conversations import Conversation
from Models.ConversationMessages import ConversationMessage
from Models.BanedUsers import BAN_REASONS, REPORT_TYPES_BY_BAN_REASONS, BanedUser
from PosterModels.SortedHashtags import SortedHashtag
import config as config
from utils.db_helper import queri_to_list
import collections
from utils.get_hasgtags import get_hashtags, get_sorted_hashtags
from utils.GettingUserInfo.keyboards import add_ban_buttons
from peewee import fn, JOIN
from PosterModels.RepostedToConversationsPosts import RepostedToConversationPost
from utils.text_cutter import cut

MAX_BUTTON_LENGTH = 40


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
        keyboard.add_callback_button(label='&#128336; В отложку',
                                     color=VkKeyboardColor.POSITIVE,
                                     payload={"command": "publish_post_pending", "post_id": post.id})

        keyboard.add_line()
        keyboard.add_callback_button(label='# Редактировать хэштеги',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": "edit_hashtags", "post_id": post.id, 'page': 1})
        if PostsHashtag.select().where(PostsHashtag.post==post).limit(1).count() > 0:
            keyboard.add_callback_button(label='&#10060; Очистить',
                                         color=VkKeyboardColor.SECONDARY,
                                         payload={"command": "clear_hashtags", "post_id": post.id, 'page': 1})
        keyboard.add_line()

    keyboard.add_callback_button(label='&#128214; Информация о пользователе',
                                 color=VkKeyboardColor.SECONDARY,
                                 payload={"command": "show_user_info", "post_id": post.id})

    keyboard.add_line()
    keyboard.add_callback_button(label='&#128172; Переслать в обсуждение',
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
        keyboard.add_callback_button(label=cut(ht, MAX_BUTTON_LENGTH),
                                     color=color,
                                     payload={"command": command, "post_id": post.id, 'hashtag': ht, 'page': page})

    # next_page_hashtags = hashtags_pages[(page + 1)]
    next_page_exists = len(hashtags_pages) > page

    if page > 1 or next_page_exists:
        keyboard.add_line()

    if page > 1:
        keyboard.add_callback_button(label=f'<< Назад ({page - 1})',
                                     color=VkKeyboardColor.PRIMARY,
                                     payload={"command": "edit_hashtags", "post_id": post.id, 'page': page - 1})

    if next_page_exists:
        keyboard.add_callback_button(label=f'Далее ({len(hashtags_pages) - page}) >>',
                                     color=VkKeyboardColor.PRIMARY,
                                     payload={"command": "edit_hashtags", "post_id": post.id, 'page': page + 1})

    return keyboard.get_keyboard()


def user_info_menu(post: Post):
    keyboard = VkKeyboard(one_time=False, inline=True)

    keyboard.add_callback_button(label='<< Назад',
                                 color=VkKeyboardColor.PRIMARY,
                                 payload={"command": "show_main_menu", "post_id": post.id})

    keyboard.add_callback_button(label='ЗАБАНИТЬ',
                                 color=VkKeyboardColor.NEGATIVE,
                                 payload={"command": "show_ban_from_post_menu", "post_id": post.id})

    return keyboard.get_keyboard()


def user_ban_menu(post: Post):
    keyboard = VkKeyboard(one_time=False, inline=True)

    keyboard.add_callback_button(label='<< Назад',
                                 color=VkKeyboardColor.PRIMARY,
                                 payload={"command": "show_user_info", "post_id": post.id})

    keyboard.add_callback_button(label='В главное меню',
                                 color=VkKeyboardColor.PRIMARY,
                                 payload={"command": "show_main_menu", "post_id": post.id})

    payload = {"command": "ban_user_from_suggest_post", "post_id": post.id}
    add_ban_buttons(keyboard=keyboard, user=post.user, payload=payload)

    return keyboard.get_keyboard()


def conversation_menu(post: Post, page: int = 1):
    keyboard = VkKeyboard(one_time=False, inline=True)

    keyboard.add_callback_button(label='<< Вернуться в главное меню',
                                 color=VkKeyboardColor.PRIMARY,
                                 payload={"command": "show_main_menu", "post_id": post.id})

    conversations_of_post = Conversation.select(Conversation.id).join(
        ConversationMessage).where(
        (ConversationMessage.from_post == post) &
        (ConversationMessage.is_deleted == False)).distinct().execute()
    processed_conversations_of_post_tmp = queri_to_list(conversations_of_post, 'id')

    reposted_posts = RepostedToConversationPost.select(RepostedToConversationPost.conversation_id).where(
        RepostedToConversationPost.post_id == post.id
    ).distinct().execute()
    conversations_of_post_tmp = queri_to_list(reposted_posts, 'conversation_id')

    pages = _conversations_by_pages(post)
    if len(pages) == 0:
        current_page = []
    else:
        page = min(max(pages.keys()), page)
        current_page = pages[page]

    for conversation in current_page:
        keyboard.add_line()
        message_url = ''
        if conversation.id in processed_conversations_of_post_tmp:
            messages = ConversationMessage.select().where(
                ConversationMessage.from_post == post
            ).order_by(ConversationMessage.date.desc()).limit(1).execute()
            if len(messages) > 0:
                message_url = messages[0].get_url()
        elif conversation.id in conversations_of_post_tmp:
            messages = RepostedToConversationPost.select().where(
                (RepostedToConversationPost.post_id == post.id) &
                (RepostedToConversationPost.conversation_id == conversation.id)
            ).order_by(RepostedToConversationPost.id.desc()).limit(1).execute()
            if len(messages) > 0:
                message_url = ConversationMessage.generate_url(
                    conversation=conversation,
                    message_id=messages[0].conversation_message_id.replace(f'{conversation.id}_', ''))

        if message_url != '':
            keyboard.add_openlink_button(
                link=message_url,
                label=cut(str(conversation), MAX_BUTTON_LENGTH),
            )

        else:
            keyboard.add_callback_button(
                label=cut(str(conversation), MAX_BUTTON_LENGTH),
                color=VkKeyboardColor.SECONDARY,
                payload={
                    "command": 'repost_to_conversation',
                    "post_id": post.id,
                    'conversation_id': conversation.id,
                    'page': page})

    next_page_exists = len(pages) > page
    if page > 1 or next_page_exists:
        keyboard.add_line()

    if page > 1:
        keyboard.add_callback_button(
            label=f'<< Назад ({page - 1})',
            color=VkKeyboardColor.PRIMARY,
            payload={"command": "show_conversation_menu", "post_id": post.id, 'page': page - 1})

    if next_page_exists:
        keyboard.add_callback_button(
            label=f'Далее ({len(pages) - page}) >>',
            color=VkKeyboardColor.PRIMARY,
            payload={"command": "show_conversation_menu", "post_id": post.id, 'page': page + 1})

    return keyboard.get_keyboard()


@functools.lru_cache()
def _hashtags_by_pages(post: Post) -> dict[int, list]:
    sorted_hashtags = queri_to_list(SortedHashtag.select().where(SortedHashtag.post_id == post.id), column='hashtag')
    for ht in get_hashtags():
        if ht not in sorted_hashtags:
            sorted_hashtags.append(ht)

    return _paginate(sorted_hashtags)


@functools.lru_cache()
def _conversations_by_pages(post: Post) -> dict[int, list]:
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

    conversations = []
    for conv in conversations_query.execute():
        conversations.append(conv)

    return _paginate(conversations)


def _paginate(objects: list, paginate_by: int = 4) -> dict[int, list]:
    pages = collections.defaultdict(list)

    current_page = 1
    current_count = 0
    for ht in objects:
        if current_count >= paginate_by:
            current_count = 0
            current_page += 1
        pages[current_page].append(ht)
        current_count += 1

    return pages


if __name__ == '__main__':
    _conversations_by_pages(None)
