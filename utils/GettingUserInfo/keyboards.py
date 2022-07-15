from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from Models.Posts import Post, PostStatus
from Models.Users import User
from Models.Comments import Comment
from Models.ConversationMessages import ConversationMessage
from Models.ChatMessages import ChatMessage
from utils.db_helper import queri_to_list
import collections
from utils.get_hasgtags import get_hashtags, get_sorted_hashtags


def main_menu_keyboard(user: User):
    keyboard = VkKeyboard(one_time=False, inline=True)

    published_posts = Post.select(Post.id).where((Post.user == user)
                                                 & (Post.suggest_status.is_null())).limit(1)
    need_new_line = False
    if len(published_posts) > 0:
        if need_new_line:
            keyboard.add_line()
        keyboard.add_callback_button(label='Опубликованные посты',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": "show_ui_published_posts", "user_id": user.id})
        need_new_line = True

    unpublished_posts = Post.select(Post.id).where((Post.user == user)
                                                   & ((Post.suggest_status == PostStatus.REJECTED.value) |
                                                      (Post.suggest_status == PostStatus.SUGGESTED.value))
                                                   ).limit(1)

    if len(unpublished_posts) > 0:
        if need_new_line:
            keyboard.add_line()
        keyboard.add_callback_button(label='Неопубликованные посты',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": "show_ui_unpublished_posts", "user_id": user.id})
        need_new_line = True

    comments = Comment.select(Comment.id).where(Comment.user == user).limit(1)
    if len(comments) > 0:
        if need_new_line:
            keyboard.add_line()
        keyboard.add_callback_button(label='Комментарии к постам',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": "show_ui_post_comments", "user_id": user.id})
        need_new_line = True

    conv_mes = ConversationMessage.select(ConversationMessage.id).where(ConversationMessage.user == user).limit(1)
    if len(conv_mes) > 0:
        if need_new_line:
            keyboard.add_line()
        keyboard.add_callback_button(label='Сообщения в обсуждениях',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": "show_ui_conv_messages", "user_id": user.id})
        need_new_line = True

    conv_mes = ConversationMessage.select(ConversationMessage.id).where(ConversationMessage.user == user).limit(1)
    if len(conv_mes) > 0:
        if need_new_line:
            keyboard.add_line()
        keyboard.add_callback_button(label='Сообщения в чатах',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": "show_ui_chat_messages", "user_id": user.id})
        need_new_line = True

    if need_new_line:
        keyboard.add_line()
    keyboard.add_callback_button(label='Обновить',
                                 color=VkKeyboardColor.PRIMARY,
                                 payload={"command": "show_ui_user_short_info", "user_id": user.id})

    return keyboard.get_keyboard()

# def hashtag_menu(post: Post, page: int = 1):
#     keyboard = VkKeyboard(one_time=False, inline=True)
#
#     keyboard.add_callback_button(label='Закончить',
#                                  color=VkKeyboardColor.POSITIVE,
#                                  payload={"command": "show_main_menu", "post_id": post.id})
#
#     keyboard.add_callback_button(label='Закончить и опубликовать',
#                                  color=VkKeyboardColor.POSITIVE,
#                                  payload={"command": "publish_post", "post_id": post.id})
#
#     added_hashtags = queri_to_list(post.hashtags)
#     hashtags_pages = _hashtags_by_pages(post)
#     page = min(max(hashtags_pages.keys()), page)
#     current_page_hashtags = hashtags_pages[page]
#
#     for ht in current_page_hashtags:
#         keyboard.add_line()
#         if ht in added_hashtags:
#             command = 'remove_hashtag'
#             color = VkKeyboardColor.PRIMARY
#         else:
#             command = 'add_hashtag'
#             color = VkKeyboardColor.SECONDARY
#         keyboard.add_callback_button(label=ht,
#                                      color=color,
#                                      payload={"command": command, "post_id": post.id, 'hashtag': ht, 'page': page})
#
#     next_page_hashtags = hashtags_pages[(page + 1)]
#     next_page_exists = len(next_page_hashtags) > 0
#
#     if page > 1 or next_page_exists:
#         keyboard.add_line()
#
#     if page > 1:
#         keyboard.add_callback_button(label='<< Назад',
#                                      color=VkKeyboardColor.SECONDARY,
#                                      payload={"command": "edit_hashtags", "post_id": post.id, 'page': page - 1})
#
#     if next_page_exists:
#         keyboard.add_callback_button(label='Далее >>',
#                                      color=VkKeyboardColor.SECONDARY,
#                                      payload={"command": "edit_hashtags", "post_id": post.id, 'page': page + 1})
#
#     return keyboard.get_keyboard()
#
#
# def user_info_menu(post: Post, page: int = 1):
#     keyboard = VkKeyboard(one_time=False, inline=True)
#
#     keyboard.add_callback_button(label='<< Назад',
#                                  color=VkKeyboardColor.SECONDARY,
#                                  payload={"command": "show_main_menu", "post_id": post.id})
#
#     return keyboard.get_keyboard()
#
#
# def _hashtags_by_pages(post: Post) -> dict[int, list]:
#     count_per_page = 4
#     sorted_hashtags = queri_to_list(SortedHashtag.select().where(SortedHashtag.post_id == post.id), column='hashtag')
#     for ht in get_hashtags():
#         if ht not in sorted_hashtags:
#             sorted_hashtags.append(ht)
#
#     pages = collections.defaultdict(list)
#
#     current_page = 1
#     current_count = 0
#     for ht in sorted_hashtags:
#         if current_count < count_per_page:
#             pages[current_page].append(ht)
#             current_count += 1
#         else:
#             current_count = 0
#             current_page += 1
#
#     return pages
