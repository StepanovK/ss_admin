from . import users
from . import posts
from . import attachments
from Models.Comments import Comment
from Models.Posts import Post
import datetime
from config import logger
from typing import Union


def get_comment(owner_id, object_id, vk_connection):
    try:
        comment = Comment.get(owner_id=owner_id, vk_id=object_id)
    except Comment.DoesNotExist:
        comment = add_comment(owner_id, object_id, vk_connection)
    return comment


def add_comment(owner_id: int, object_id: int, vk_connection):
    found_comment = None
    if object_id is not None and int(object_id) != 0:
        try:
            vk_objects = vk_connection.wall.getComment(owner_id=owner_id, comment_id=object_id)
            items = vk_objects.get('items', [])
            if len(items) == 1:
                found_comment = parse_comment(items[0], vk_connection)
        except Exception as ex:
            logger.error(f'Failed to get comment data {object_id} by reason: {ex}')
    return found_comment


def parse_comment(comment_obj: dict, vk_connection):
    comment_attr = get_comment_attributes(comment_obj)
    post = posts.get_post(comment_attr['owner_id'], comment_attr['post_id'], vk_connection)
    comment, comment_created = Comment.get_or_create(post=post,
                                                     owner_id=comment_attr['owner_id'],
                                                     vk_id=comment_attr['vk_id'])
    comment.text = comment_attr['text']
    comment.date = comment_attr['date']

    if comment_attr['user_id']:
        user = users.get_or_create_user(comment_attr['user_id'], vk_connection)
        comment.user = user

    if comment_attr['replied_comment']:
        replied_comment = get_comment(comment_attr['owner_id'],
                                      comment_attr['replied_comment'],
                                      vk_connection)
        comment.replied_comment = replied_comment

    if comment_attr['replied_to_user']:
        replied_to_user = users.get_or_create_user(comment_attr['replied_to_user'], vk_connection)
        comment.replied_to_user = replied_to_user

    comment.save()

    attachments.parce_added_attachments(comment, comment_obj.get('attachments', []))

    return comment


def parse_delete_comment(comment_obj: dict, vk_connection):
    comment = get_comment(owner_id=comment_obj['owner_id'],
                          object_id=comment_obj['id'],
                          vk_connection=vk_connection)
    if comment is not None:
        comment.is_deleted = True
        comment.save()


def parse_restore_comment(comment_obj: dict, vk_connection):
    comment = get_comment(owner_id=comment_obj['owner_id'],
                          object_id=comment_obj['id'],
                          vk_connection=vk_connection)
    if comment is not None and comment.is_deleted:
        comment.is_deleted = False
        comment.save()


def get_comment_attributes(comment_obj: dict):
    attributes = {
        'vk_id': comment_obj.get('id', 0),
        'owner_id': comment_obj.get('post_owner_id', 0),
        'post_id': comment_obj.get('post_id', 0),
        'text': comment_obj.get('text', ''),
        'date': datetime.datetime.fromtimestamp(comment_obj.get('date', 0)),
        'replied_comment': comment_obj.get('reply_to_comment', 0),
        'reply_to_user': comment_obj.get('reply_to_user', 0),
        'user_id': None,
        'replied_to_user': None
    }

    if attributes['owner_id'] == 0:
        attributes['owner_id'] = comment_obj.get('owner_id', 0)

    from_id = comment_obj.get('from_id', 0)
    attributes['user_id'] = from_id if isinstance(from_id, int) and from_id > 0 else None

    replied_to_user = comment_obj.get('reply_to_user', 0)
    attributes['replied_to_user'] = replied_to_user if isinstance(replied_to_user,
                                                                  int) and replied_to_user > 0 else None

    return attributes


def mark_posts_comments_as_deleted(post: Post, is_deleted: Union[None, bool] = None):
    del_mark = post.is_deleted if is_deleted is None else is_deleted
    posts_comments = Comment.select().where((Comment.post == post) & (Comment.is_deleted != del_mark))
    for comment in posts_comments:
        comment.is_deleted = del_mark
        comment.save()
