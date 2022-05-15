from Models.Admins import Admin
from Models.Users import User
from Models.UploadedFiles import UploadedFile
from Models.Posts import Post, PostStatus
from Models.Comments import Comment
import Models.Relations as Relations
import datetime
from config import logger
from typing import Union


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
            logger.error(f'Не удалось получить данные поста {full_id} по причине: {ex}')
    return found_post


def parse_wall_post(wall_post: dict, vk_connection=None):
    post_attributes = get_wall_post_attributes(wall_post)

    post_id = Post.generate_id(vk_id=post_attributes['vk_id'], owner_id=post_attributes['owner_id'])

    post, post_created = Post.get_or_create(id=post_id)
    post.vk_id = post_attributes['vk_id']
    post.owner_id = post_attributes['owner_id']
    post.text = post_attributes['text']
    post.date = post_attributes['date']
    post.marked_as_ads = post_attributes['marked_as_ads']
    post.suggest_status = post_attributes['suggest_status']
    post.posted_by = post_attributes['admin']

    if post_attributes['user_id']:
        user = get_or_create_user(post_attributes['user_id'], vk_connection)
        post.user = user
    else:
        post.anonymously = True

    post.save()

    parce_added_attachments(post, wall_post.get('attachments', []))

    parce_post_likes(post, wall_post.get('likers', []), vk_connection)

    return post


def get_wall_post_attributes(wall_post: dict):
    post_attributes = {
        'vk_id': wall_post.get('id', 0),
        'owner_id': str(wall_post.get('owner_id', '')),
        'text': wall_post.get('text', ''),
        'date': datetime.datetime.fromtimestamp(wall_post.get('date', 0)),
        'marked_as_ads': bool(wall_post.get('marked_as_ads', False)),
        'suggest_status': None,
        'admin': None,
        'user_id': None
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
        post_attributes['admin'], _ = Admin.get_or_create(id=created_by, user=get_or_create_user(vk_id=created_by))

    return post_attributes


def parce_added_attachments(post_or_comment: Union[Post, Comment], attachments: list):
    for attachment in attachments:
        attachment_type = attachment.get('type')
        if attachment_type in UploadedFile.available_types():
            media_file = parse_vk_attachment(attachment)
            if media_file is not None:
                if media_file.user is None:
                    media_file.user = post_or_comment.user
                    media_file.save()
                Relations.add_attachment(post_or_comment, media_file)


def parse_vk_attachment(vk_attachment):
    attachment_type = vk_attachment.get('type')
    if attachment_type == 'audio' and 'audio' in vk_attachment:
        vk_attachment_info = vk_attachment.get('audio')
        parse_method = parse_vk_audio_attachment
    elif attachment_type == 'doc' and 'doc' in vk_attachment:
        vk_attachment_info = vk_attachment.get('doc')
        parse_method = parse_vk_doc_attachment
    elif attachment_type == 'photo' and 'photo' in vk_attachment:
        vk_attachment_info = vk_attachment.get('photo')
        parse_method = parse_vk_photo_attachment
    elif attachment_type == 'video' and 'video' in vk_attachment:
        vk_attachment_info = vk_attachment.get('video')
        parse_method = parse_vk_video_attachment
    else:
        logger.warning(f'Не удалось обработать вложение {attachment_type}')
        return
    main_attributes = get_main_attachment_attributes(vk_attachment_info)

    uploaded_file, created = UploadedFile.get_or_create(type=attachment_type,
                                                        vk_id=main_attributes['vk_id'],
                                                        owner_id=main_attributes['owner_id'])
    uploaded_file.date = main_attributes['date']
    uploaded_file.access_key = main_attributes['access_key']
    parse_method(uploaded_file, vk_attachment_info)
    uploaded_file.save()
    return uploaded_file


def get_main_attachment_attributes(vk_attachment_info: dict):
    attachment_attributes = {
        'vk_id': vk_attachment_info.get('id'),
        'date': datetime.datetime.fromtimestamp(vk_attachment_info.get('date', 0)),
        'access_key': vk_attachment_info.get('access_key'),
        'owner_id': vk_attachment_info.get('owner_id')
    }
    return attachment_attributes


def parse_vk_audio_attachment(uploaded_file: UploadedFile, vk_audio_info: dict):
    title = vk_audio_info.get('title', '')
    artist = vk_audio_info.get('artist', '')
    uploaded_file.file_name = f'{artist} - {title}' if artist != '' else title
    uploaded_file.url = vk_audio_info.get('track_code')


def parse_vk_doc_attachment(uploaded_file: UploadedFile, vk_doc_info: dict):
    uploaded_file.file_name = vk_doc_info.get('title', '')
    uploaded_file.platform = vk_doc_info.get('ext')
    uploaded_file.url = vk_doc_info.get('url')
    previews = vk_doc_info.get('preview', {})
    photos = previews.get('photo', {})
    sizes = photos.get('sizes', [])
    if len(sizes) > 0:
        max_size = sizes[-1]
        uploaded_file.preview_url = max_size.get('src', '')


def parse_vk_photo_attachment(uploaded_file: UploadedFile, vk_photo_info: dict):
    uploaded_file.generate_file_name()
    sizes = vk_photo_info.get('sizes', [])
    if len(sizes) > 0:
        max_size = sizes[-1]
        uploaded_file.url = max_size.get('url', '')
    if len(sizes) > 1:
        min_size = sizes[0]
        uploaded_file.preview_url = min_size.get('url', '')


def parse_vk_video_attachment(uploaded_file: UploadedFile, vk_video_info: dict):
    uploaded_file.description = vk_video_info.get('description', '')
    uploaded_file.platform = vk_video_info.get('platform')
    uploaded_file.file_name = vk_video_info.get('title', '')
    uploaded_file.url = vk_video_info.get('track_code', '')
    if uploaded_file.file_name == '':
        uploaded_file.generate_file_name()
    sizes = vk_video_info.get('image', [])
    if len(sizes) > 0:
        max_size = sizes[-1]
        uploaded_file.preview_url = max_size.get('url', '')


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
            logger.error(f'Не удалось получить данные комментария {object_id} по причине: {ex}')
    return found_comment


def parse_comment(comment_obj: dict, vk_connection):
    comment_attr = get_comment_attributes(comment_obj)
    post = get_post(comment_attr['owner_id'], comment_attr['post_id'], vk_connection)
    comment, comment_created = Comment.get_or_create(post=post,
                                                     owner_id=comment_attr['owner_id'],
                                                     vk_id=comment_attr['vk_id'])
    comment.text = comment_attr['text']
    comment.date = comment_attr['date']

    if comment_attr['user_id']:
        user = get_or_create_user(comment_attr['user_id'], vk_connection)
        comment.user = user

    if comment_attr['replied_comment']:
        replied_comment = get_comment(comment_attr['owner_id'],
                                      comment_attr['replied_comment'],
                                      vk_connection)
        comment.replied_comment = replied_comment

    if comment_attr['replied_to_user']:
        replied_to_user = get_or_create_user(comment_attr['replied_to_user'], vk_connection)
        comment.replied_to_user = replied_to_user

    comment.save()

    parce_added_attachments(comment, comment_obj.get('attachments', []))

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


def parce_post_likes(post: Post, likers: list, vk_connection=None):
    for liker in likers:
        user_id = liker.get('uid')
        if isinstance(user_id, int) and user_id > 0:
            user = get_or_create_user(user_id, vk_connection)
            Relations.add_like(post, user)


def parse_like_add(action, vk_connection=None):
    if action['object_type'] == 'post':
        owner_id = action['object_owner_id']
        object_id = action['object_id']
        liked_object = get_post(owner_id, object_id, vk_connection)
    # TODO Добавить лайки комментов
    # elif action['object_type'] == 'comment':
    #     try:
    #         liked_object = Comm.get(owner_id=action['object_owner_id'], vk_id=action['object_id'])
    #     except Post.DoesNotExist:
    #         liked_object = None
    else:
        liked_object = None

    if liked_object is not None:
        user = get_or_create_user(action['liker_id'], vk_connection)
        Relations.add_like(liked_object, user)


def parse_like_remove(action, vk_connection=None):
    if action['object_type'] == 'post':
        owner_id = action['object_owner_id']
        object_id = action['object_id']
        try:
            liked_object = Post.get(owner_id=owner_id, vk_id=object_id)
        except Post.DoesNotExist:
            liked_object = add_post(owner_id, object_id, vk_connection)
    # TODO Добавить лайки комментов
    # elif action['object_type'] == 'comment':
    #     try:
    #         liked_object = Comm.get(owner_id=action['object_owner_id'], vk_id=action['object_id'])
    #     except Post.DoesNotExist:
    #         liked_object = None
    else:
        liked_object = None

    if liked_object is not None:
        user = get_or_create_user(action['liker_id'], vk_connection)
        Relations.remove_like(liked_object, user)


def get_or_create_user(vk_id: int, vk_connection=None):
    try:
        user = User.get_by_id(vk_id)
    except User.DoesNotExist:
        user = User.create(id=vk_id)
        if vk_connection is not None:
            update_user_info_from_vk(user, vk_id, vk_connection)
            user.save()

    return user


def vk_get_user_info(user_id: int, vk_connection):
    user_info = {
        'id': user_id,
        'first_name': '',
        'last_name': '',
        'photo_max': '',
        'last_seen': '',
        'birth_date': None,
        'city': '',
        'can_write_private_message': False,
        'sex': '',
        'user_info_was_found': False
    }
    fields = 'id, first_name,last_name, photo_max, last_seen, domain, ' \
             'city, can_write_private_message, online, sex, bdate, ' \
             'photo_max_orig, photo_50'
    try:
        response = vk_connection.users.get(user_ids=user_id, fields=fields)
        if isinstance(response, list) and len(response) > 0:
            user_info.update(response[0])
            city = user_info['city']
            user_info['city'] = city.get('title', '') if isinstance(city, dict) else str(city)
            sex = user_info.get('sex', 0)
            user_info['sex'] = 'female' if sex == 1 else 'male' if sex == 2 else ''
            user_info['can_write_private_message'] = bool(user_info.get('can_write_private_message', 0))
            user_info['user_info_was_found'] = True
            if 'bdate' in user_info:
                time_parts = str(user_info.get('bdate', '')).split('.')
                if len(time_parts) == 3:
                    user_info['birth_date'] = datetime.date(int(time_parts[2]), int(time_parts[1]),
                                                            int(time_parts[0]))
                elif len(time_parts) == 2:
                    user_info['birth_date'] = datetime.date(1900, int(time_parts[1]), int(time_parts[0]))

    except Exception as ex:
        logger.error(f"Ошибка получения информации о пользователе id{user_id}: {ex}")
    return user_info


def update_user_info_from_vk(user: User, vk_id: int, vk_connection):
    user_info = vk_get_user_info(vk_id, vk_connection)
    if user_info.get('user_info_was_found', False):
        user.first_name = user_info.get('first_name')
        user.last_name = user_info.get('last_name')
        user.city = user_info.get('city', '')
        user.birth_date = user_info.get('birth_date')
        user.sex = user_info.get('sex', '')
        user.is_active = user_info.get('deactivated') is None
        user.domain = user_info.get('domain', '')
