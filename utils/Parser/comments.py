from . import users
from . import posts
from . import attachments
from Models.Comments import Comment
from Models.Posts import Post
from Models.base import db
from Models.Relations import CommentsLike
import datetime
from config import logger
from typing import Union, Optional


def load_post_comments(post: Post, vk_connection, group_id: Optional[int] = None):
    loaded_comments = []
    count_for_get = 100  # min = 10, max = 100
    offset = 0
    _group_id = -group_id if group_id else post.owner_id
    params = {'owner_id': _group_id,
              'post_id': post.vk_id,
              'need_likes': 1,
              'count': count_for_get,
              'sort': 'asc',
              'extended': 1,
              'fields': users.users_fields(),
              'thread_items_count': 10}
    while True:
        with db.atomic():
            vk_comments = vk_connection.wall.getComments(offset=offset, **params)
            for user_info in vk_comments['profiles']:
                user = users.add_user_by_info(vk_connection, user_info)
            for vk_comment in vk_comments['items']:
                comment = parse_comment(vk_comment, vk_connection)
                loaded_comments.append(comment)

                thread = vk_comment.get('thread', {})
                comments_in_thread = []
                if 1 < thread.get('count', 0) < 10:
                    comments_in_thread = thread.get('items', [])
                elif thread.get('count', 0) > 10:
                    vk_comment_with_thread = vk_connection.wall.getComments(comment_id=vk_comment['id'], **params)
                    comments_in_thread = vk_comment_with_thread.get('items', [])

                for vk_comment_in_thread in comments_in_thread:
                    comment_in_thread = parse_comment(vk_comment_in_thread, vk_connection)
                    loaded_comments.append(comment_in_thread)

        offset += count_for_get
        if len(vk_comments['items']) < count_for_get:
            break
    return loaded_comments


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

    if 'likes' in comment_obj and comment_obj['likes'].get('count', 0) > 0:
        now_likes = CommentsLike.select(CommentsLike.id).where(CommentsLike.liked_object == comment).execute()
        now_likes_count = len(now_likes)
        count = comment_obj['likes'].get('count', 0)
        if now_likes_count < count:
            def_user = users.get_or_create_user(vk_id=1, vk_connection=vk_connection)
            for i in range(now_likes_count, count):
                CommentsLike.create(liked_object=comment, user=def_user)

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
