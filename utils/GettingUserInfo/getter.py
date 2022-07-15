from Models.Comments import Comment
from Models.Users import User
from Models.Posts import Post, PostStatus
from Models.Relations import PostsLike, CommentsLike
from Models.Subscriptions import Subscription
from config import logger
import datetime
import random


def send_user_info(user, vk_connection, peer_id: int):
    short_user_info = get_short_user_info(user)
    try:
        message_id = vk_connection.messages.send(peer_id=peer_id,
                                                 message=short_user_info,
                                                 keyboard=None,
                                                 random_id=random.randint(10 ** 5, 10 ** 6))
    except Exception as ex:
        logger.warning(f'Failed send message peer_id={peer_id}\n{ex}')


def get_user_from_message(message_text: str):
    user_str = message_text
    if user_str.startswith('id'):
        user_str = user_str.replace('id', '')

    if user_str.isdigit():
        try:
            user = User.get(id=int(user_str))
            return user
        except User.DoesNotExist:
            pass

    if user_str.startswith('https://vk.com/'):
        user_str = user_str.replace('https://vk.com/', '')
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
        elif subscribe.date.date == datetime.date(2000, 1, 1):
            date_sub = 'Давно'
        else:
            date_sub = f'{subscribe.date:%Y-%m-%d}'
        subscribe_history_list.append(f'{date_sub} {state}')

    mes_text = f'Информация о пользователе {user}:\n'

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
