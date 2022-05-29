from Models.UploadedFiles import UploadedFile
from Models.Posts import Post
from Models.Comments import Comment
import Models.Relations as Relations
from utils.config import logger
from typing import Union
import datetime
import json


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
    elif attachment_type == 'poll' and 'poll' in vk_attachment:
        vk_attachment_info = vk_attachment.get('poll')
        parse_method = parse_vk_poll_attachment
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
    uploaded_file.url = vk_audio_info.get('track_code', '')


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


def parse_vk_poll_attachment(uploaded_file: UploadedFile, vk_poll_info: dict):
    uploaded_file.file_name = get_file_name_for_poll_object(vk_poll_info)
    uploaded_file.description = json.dumps(vk_poll_info)

    images = vk_poll_info.get('photo', {}).get('images', [])
    if len(images) > 0:
        max_size = images[-1]
        uploaded_file.preview_url = max_size.get('url', '')


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


def get_file_name_for_poll_object(vk_poll_info):
    """
    Метод возвращает имя в виде "Вопрос (Ответ1, Ответ2,.... ОтветН)", обрезая ответы так,
     чтобы влезло в длину имени файла (255 символов)
    :param vk_poll_info:
    :return:
    """
    free_length = 255
    question = vk_poll_info.get('question')
    free_length -= len(question)
    answers = []
    for answer in vk_poll_info.get('answers', []):
        answers.append(answer.get('text', ''))
    answers_separator = '; '
    free_length_for_answers = free_length - 3 + len(answers_separator)  # - пробел и две скобки + лишний разделитель
    free_length_for_answer = free_length_for_answers // len(answers) if len(answers) > 0 else 0
    for i in range(len(answers)):
        answers[i] = answers[i][0:free_length_for_answer - len(answers_separator)]
    str_answers = answers_separator.join(answers)
    file_name = f'{question} ({str_answers})'
    return file_name
