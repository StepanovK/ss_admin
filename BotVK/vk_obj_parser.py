from Models.Users import User
from Models.UploadedFiles import UploadedFile
from Models.Posts import Post
from Models.SuggestedPosts import SuggestedPost
import Models.Relations as Relations
from typing import Union
import datetime
from config import logger


def parse_wall_post(post: Union[Post, SuggestedPost], wall_post, vk_connection):
    post.id = wall_post['id']
    post.text = wall_post['text']
    user = get_or_create_user(wall_post['from_id'], vk_connection)
    post.user = user
    post.date = datetime.datetime.fromtimestamp(wall_post['date'])
    post.owner_id = str(wall_post['owner_id'])

    post.save(force_insert=True)

    for attachment in wall_post.get('attachments', []):
        attachment_type = attachment.get('type')
        if attachment_type in UploadedFile.available_types():
            media_file = UploadedFile.create(user=user)
            parse_vk_attachment(media_file, attachment)
            media_file.save()

            Relations.add_attachment(post, media_file)

            # sizes = attachment.get('photo', {}).get('sizes', [])
            # if len(sizes) > 0:
            #     max_size = sizes[-1]
            #     # try:
            #     #     photo = download(max_size['url'], out=cache_dir)
            #     #     photo = photo.replace('/', '\\')
            #     # except Exception as _ex:
            #     #     photo = None
            #     #     # logger.error(f'Ошибка при загрузки фото: \n{attachment} \n{_ex}')
            #     # if photo:
            #     #     self.photo.append(photo)
            #     #     # with open(photo, 'rb') as photo_file:
            #     #     #     self.photo.append(photo_file)
            #     #     # os.remove(photo)


def parse_vk_attachment(uploaded_file: UploadedFile, vk_attachment):
    attachment_type = vk_attachment.get('type')
    uploaded_file.type = attachment_type
    if attachment_type == 'audio' and 'audio' in vk_attachment:
        audio_info = vk_attachment.get('audio')
        parse_vk_audio_attachment(uploaded_file, audio_info)
    elif attachment_type == 'doc' and 'doc' in vk_attachment:
        doc_info = vk_attachment.get('doc')
        parse_vk_doc_attachment(uploaded_file, doc_info)
    elif attachment_type == 'photo' and 'photo' in vk_attachment:
        photo_info = vk_attachment.get('photo')
        parse_vk_photo_attachment(uploaded_file, photo_info)
    elif attachment_type == 'video' and 'video' in vk_attachment:
        video_info = vk_attachment.get('video')
        parse_vk_video_attachment(uploaded_file, video_info)


def parse_vk_audio_attachment(uploaded_file: UploadedFile, vk_audio_info: dict):
    uploaded_file.vk_id = vk_audio_info.get('id')
    uploaded_file.date = datetime.datetime.fromtimestamp(vk_audio_info.get('date', 0))
    uploaded_file.owner_id = vk_audio_info.get('owner_id', '')
    title = vk_audio_info.get('title', '')
    artist = vk_audio_info.get('artist', '')
    uploaded_file.file_name = f'{artist} - {title}' if artist != '' else title
    uploaded_file.url = vk_audio_info.get('track_code')


def parse_vk_doc_attachment(uploaded_file: UploadedFile, vk_doc_info: dict):
    uploaded_file.vk_id = vk_doc_info.get('id')
    uploaded_file.date = datetime.datetime.fromtimestamp(vk_doc_info.get('date', 0))
    uploaded_file.access_key = vk_doc_info.get('access_key')
    uploaded_file.owner_id = vk_doc_info.get('owner_id', '')
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
    uploaded_file.vk_id = vk_photo_info.get('id', 0)
    uploaded_file.date = datetime.datetime.fromtimestamp(vk_photo_info.get('date', 0))
    uploaded_file.access_key = vk_photo_info.get('access_key')
    uploaded_file.owner_id = vk_photo_info.get('owner_id', '')
    uploaded_file.generate_file_name()
    sizes = vk_photo_info.get('sizes', [])
    if len(sizes) > 0:
        max_size = sizes[-1]
        uploaded_file.url = max_size.get('url', '')
    if len(sizes) > 1:
        min_size = sizes[0]
        uploaded_file.preview_url = min_size.get('url', '')


def parse_vk_video_attachment(uploaded_file: UploadedFile, vk_video_info: dict):
    uploaded_file.vk_id = vk_video_info.get('id', 0)
    uploaded_file.date = datetime.datetime.fromtimestamp(vk_video_info.get('date', 0))
    uploaded_file.access_key = vk_video_info.get('access_key')
    uploaded_file.owner_id = vk_video_info.get('owner_id', '')
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
