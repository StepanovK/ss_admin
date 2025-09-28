from Models.Admins import Admin
from Models.Posts import Post, PostStatus, PostsHashtag
from Models.Relations import PostsAttachment
from Models.UploadedFiles import UploadedFile
from config import logger
from utils import get_hasgtags
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
    is_deleted = wall_post.get('is_deleted', False)
    try:
        post = Post.get(id=post_id)
    except Post.DoesNotExist:
        need_update = True
        post = Post()
    if post.is_deleted != is_deleted:
        need_update = True
    if not need_update:
        if not is_deleted and post.text != post_attributes['text']:
            need_update = True
    if not need_update and not is_deleted:
        vk_attachments = wall_post.get('attachments', [])
        vk_attachments_id = set()
        for attachment in vk_attachments:
            if attachment.get('type') != 'link':
                attachment_info = attachments.get_vk_attachment_info(attachment)
                vk_attachments_id.add(attachment_info.get('id'))

        post_attachments = UploadedFile.select(UploadedFile.vk_id).join(PostsAttachment).where(
            (PostsAttachment.is_deleted == False) & (PostsAttachment.post == post)).execute()
        post_attachments_id = [post_attachment.vk_id for post_attachment in post_attachments]
        post_attachments_id = set(post_attachments_id)

        if len(vk_attachments_id.symmetric_difference(post_attachments_id)) != 0:
            need_update = True

    if need_update:
        post = parse_wall_post(wall_post, vk_connection)
        _update_watermarked_attachments(post)

    return post, need_update


def parse_wall_post(wall_post: dict, vk_connection=None, extract_hashtags: bool = False):
    post_attributes = get_wall_post_attributes(wall_post)
    is_deleted = wall_post.get('is_deleted', False)

    post_id = Post.generate_id(vk_id=post_attributes['vk_id'], owner_id=post_attributes['owner_id'])

    post, post_created = Post.get_or_create(id=post_id)

    post.is_deleted = is_deleted

    hashtags = []

    if post_created or not is_deleted:
        post.vk_id = post_attributes['vk_id']
        post.owner_id = post_attributes['owner_id']
        post.text = post_attributes['text']
        post.date = post_attributes['date']
        post.marked_as_ads = post_attributes['marked_as_ads']
        post.geo = post_attributes['geo']
        if post_created or not is_deleted and post.suggest_status == PostStatus.REJECTED.value:
            post.suggest_status = post_attributes['suggest_status']
            post.posted_by = post_attributes['admin']

        if post_attributes['user_id']:
            user = users.get_or_create_user(post_attributes['user_id'], vk_connection)
            post.user = user
        else:
            post.anonymously = True

        if extract_hashtags:
            hashtags, new_text = extract_hashtags_from_post_text(text=post.text, replace=False)

        if post_attributes['check_sign']:
            post.anonymously = True
            post.caption_disabled = True

    post.save()

    if extract_hashtags and len(hashtags) > 0 and not post.is_deleted:
        PostsHashtag.delete().where(PostsHashtag.post == post).execute()
        ht_and_post = [(ht, post) for ht in hashtags]
        PostsHashtag.insert_many(ht_and_post, fields=[PostsHashtag.hashtag, PostsHashtag.post]).execute()

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
        'check_sign': bool(wall_post.get('check_sign', False)),
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


def extract_hashtags_from_post_text(text: str, replace: bool = False) -> tuple[list, str]:
    hashtags = []
    new_text = text
    for hashtag in get_hasgtags.get_hashtags():
        if hashtag in new_text:
            hashtags.append(hashtag)
            if replace:
                new_text = new_text.replace('\n' + hashtag, '')
                new_text = new_text.replace(hashtag + ' ', '')
                new_text = new_text.replace(hashtag, '')

    return hashtags, new_text


def parse_post_by_url(url: str, vk_connection):
    post_id = get_post_id_from_url(url=url)
    try:
        post = Post.get(id=post_id)
    except Post.DoesNotExist:
        post = None
    except Exception as ex:
        logger.warning(f'Some problem with getting post by url {url}\n{ex}')
        post = None
    need_create = post is None
    was_updated = False
    posts_info = vk_connection.wall.getById(posts=post_id)
    for post_info in posts_info:
        if need_create:
            post = parse_wall_post(wall_post=post_info, vk_connection=vk_connection, extract_hashtags=True)
        else:
            post, was_updated = update_wall_post(wall_post=post_info, vk_connection=vk_connection)

    was_created = need_create and post is not None
    return post, was_created, was_updated


def it_is_post_url(url: str) -> bool:
    pref = _post_link_prefix()
    return url.startswith(pref)


def get_post_id_from_url(url: str) -> str:
    pref = _post_link_prefix()
    post_id = url.replace(pref, '')
    return post_id


def _update_watermarked_attachments(post: Post):
    watermarked_attachments_query = UploadedFile.select().join(
        PostsAttachment).where(
        (UploadedFile.is_watermarked == True) &
        (UploadedFile.type.in_(['photo', 'video'])) &
        (PostsAttachment.post == post)).execute()
    if len(watermarked_attachments_query) == 0:
        return
    watermarked_attachments = [attachment for attachment in watermarked_attachments_query]
    post_attachments = PostsAttachment.select().where(PostsAttachment.post == post).execute()
    for post_attachment in post_attachments:
        attachment = post_attachment.attachment
        if not attachment.is_watermarked:
            source_attachments = UploadedFile.select().where(
                (UploadedFile.id.in_(watermarked_attachments)) &
                (UploadedFile.url == attachment.url) &
                (UploadedFile.is_deleted == True)
            ).limit(1).execute()
            if len(source_attachments) > 0:
                attachment.is_watermarked = True
                attachment.save()
                PostsAttachment.delete().where(
                    (PostsAttachment.post == post) &
                    (PostsAttachment.attachment == source_attachments[0])).execute()
                source_attachments[0].delete_instance()


def _post_link_prefix() -> str:
    vk_link = Post.VK_LINK
    return f'{vk_link}wall'
