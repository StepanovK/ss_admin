from Models.Users import User
from Models.UploadedFiles import UploadedFile
from Models.Posts import Post
from Models.SuggestedPosts import SuggestedPost
import Models.Relations as Relations
from typing import Union
import datetime


def parse_wall_post(post: Union[Post, SuggestedPost], wall_post, vk_connection):
    post.id = wall_post['id']
    post.text = wall_post['text']
    user = User.get_or_create_user(wall_post['from_id'], vk_connection)
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
    if attachment_type == 'photo' and 'photo' in vk_attachment:
        photo_info = vk_attachment.get('photo')
        parse_vk_photo_attachment(uploaded_file, photo_info)


def parse_vk_photo_attachment(uploaded_file: UploadedFile, vk_photo_info):
    uploaded_file.vk_id = vk_photo_info.get('id', 0)
    uploaded_file.date = datetime.datetime.fromtimestamp(vk_photo_info.get('date', 0))
    uploaded_file.access_key = vk_photo_info.get('access_key', '')
    uploaded_file.owner_id = vk_photo_info.get('owner_id', '')
    uploaded_file.generate_file_name()
    sizes = vk_photo_info.get('sizes', [])
    if len(sizes) > 0:
        max_size = sizes[-1]
        uploaded_file.url = max_size.get('url')
    if len(sizes) > 1:
        min_size = sizes[0]
        uploaded_file.preview_url = min_size.get('url')
