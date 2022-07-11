from Models.Admins import Admin
from Models.Posts import Post, PostStatus
from Models.Relations import PostsAttachment
from config import logger
from . import attachments
from . import likes
from . import users
import datetime


def get_post(owner_id, object_id, vk_connection):
    try:
        post = Post.get(owner_id=owner_id, vk_id=object_id)
    except Post.DoesNotExist:
        post = add_post(owner_id, object_id, vk_connection)
    return post


def add_post(owner_id: int, post_id: int, vk_connection):
    found_post = None
    if post_id is not None and int(post_id) != 0:
        full_id = Post.generate_id(owner_id, post_id)
        try:
            posts = vk_connection.wall.getById(posts=full_id)
            if len(posts) == 1:
                post = posts[0]
                likers = vk_connection.wall.getLikes(owner_id=owner_id, post_id=post_id, count=1000)
                post['likers'] = likers.get('users', [])
                found_post = parse_wall_post(post)
        except Exception as ex:
            logger.error(f'Failed to get post data {full_id} by reason: {ex}')
    return found_post


def update_wall_post(wall_post: dict, vk_connection=None):
    post_attributes = get_wall_post_attributes(wall_post)
    post_id = Post.generate_id(vk_id=post_attributes['vk_id'], owner_id=post_attributes['owner_id'])
    need_update = False
    try:
        post = Post.get(id=post_id)
    except Post.DoesNotExist:
        need_update = True
        post = Post()
    if 'deleted_reason' in wall_post and wall_post['deleted_reason'] != '':
        need_update = True
    if not need_update:
        if post.text != post_attributes['text']:
            need_update = True
    if not need_update:
        vk_attachments = wall_post.get('attachments', [])
        post_attachments = PostsAttachment.select().where((PostsAttachment.is_deleted == False)
                                                          & (PostsAttachment.post == post))
        if len(vk_attachments) != len(post_attachments):
            need_update = True

    if need_update:
        post = parse_wall_post(wall_post, vk_connection)

    return post, need_update


def parse_wall_post(wall_post: dict, vk_connection=None):
    post_attributes = get_wall_post_attributes(wall_post)
    is_deleted = 'deleted_reason' in wall_post and wall_post['deleted_reason'] != ''

    post_id = Post.generate_id(vk_id=post_attributes['vk_id'], owner_id=post_attributes['owner_id'])

    post, post_created = Post.get_or_create(id=post_id)

    post.is_deleted = is_deleted

    if post_created or not is_deleted:
        post.vk_id = post_attributes['vk_id']
        post.owner_id = post_attributes['owner_id']
        post.text = post_attributes['text']
        post.date = post_attributes['date']
        post.marked_as_ads = post_attributes['marked_as_ads']
        post.suggest_status = post_attributes['suggest_status']
        post.posted_by = post_attributes['admin']
        post.geo = post_attributes['geo']

        if post_attributes['user_id']:
            user = users.get_or_create_user(post_attributes['user_id'], vk_connection)
            post.user = user
        else:
            post.anonymously = True

    post.save()

    attachments.parce_added_attachments(post, wall_post.get('attachments', []))

    likes.parce_post_likes(post, wall_post.get('likers', []), vk_connection)

    return post


def get_wall_post_attributes(wall_post: dict):
    post_attributes = {
        'vk_id': wall_post.get('id', 0),
        'owner_id': wall_post.get('owner_id'),
        'text': wall_post.get('text', '').strip(),
        'date': datetime.datetime.fromtimestamp(wall_post.get('date', 0)),
        'marked_as_ads': bool(wall_post.get('marked_as_ads', False)),
        'suggest_status': None,
        'admin': None,
        'user_id': None,
        'geo': wall_post.get('geo', {}).get('coordinates'),
    }

    suggest_status = PostStatus.SUGGESTED.value if wall_post.get('post_type', '') == 'suggest' else None
    post_attributes['suggest_status'] = suggest_status

    from_id = wall_post.get('from_id', 0)
    post_attributes['user_id'] = from_id if isinstance(from_id, int) and from_id > 0 else None

    signer_id = wall_post.get('signer_id', 0)
    if post_attributes['user_id'] is None and isinstance(signer_id, int) and signer_id > 0:
        post_attributes['user_id'] = signer_id

    created_by = wall_post.get('created_by')
    if suggest_status is None and isinstance(created_by, int) and created_by > 0:
        post_attributes['admin'], _ = Admin.get_or_create(id=created_by,
                                                          user=users.get_or_create_user(vk_id=created_by))
    return post_attributes
