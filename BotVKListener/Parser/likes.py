import Models.Relations as Relations
from Models.Posts import Post
from BotVKListener.Parser import comments
from BotVKListener.Parser import users
from BotVKListener.Parser import posts
from BotVKListener.config import logger


def parce_post_likes(post: Post, likers: list, vk_connection=None):
    for liker in likers:
        user_id = liker.get('uid')
        if isinstance(user_id, int) and user_id > 0:
            user = users.get_or_create_user(user_id, vk_connection)
            Relations.add_like(post, user)


def parse_like_add(action, vk_connection=None):
    if action['object_type'] == 'post':
        owner_id = action['object_owner_id']
        object_id = action['object_id']
        liked_object = posts.get_post(owner_id, object_id, vk_connection)
    elif action['object_type'] == 'comment':
        try:
            liked_object = comments.get_comment(owner_id=action['object_owner_id'],
                                                object_id=action['object_id'],
                                                vk_connection=vk_connection)
        except Post.DoesNotExist:
            liked_object = None
    else:
        liked_object = None

    if liked_object is not None:
        user = users.get_or_create_user(action['liker_id'], vk_connection)
        Relations.add_like(liked_object, user)
        if liked_object.user == user:
            logger.info(f'Самолайк детектед! {user} лайкнул {liked_object}')


def parse_like_remove(action, vk_connection=None):
    if action['object_type'] == 'post':
        owner_id = action['object_owner_id']
        object_id = action['object_id']
        try:
            liked_object = Post.get(owner_id=owner_id, vk_id=object_id)
        except Post.DoesNotExist:
            liked_object = posts.add_post(owner_id, object_id, vk_connection)
    elif action['object_type'] == 'comment':
        try:
            liked_object = comments.get_comment(owner_id=action['object_owner_id'],
                                                object_id=action['object_id'],
                                                vk_connection=vk_connection)
        except Post.DoesNotExist:
            liked_object = None
    else:
        liked_object = None

    if liked_object is not None:
        user = users.get_or_create_user(action['liker_id'], vk_connection)
        Relations.remove_like(liked_object, user)
