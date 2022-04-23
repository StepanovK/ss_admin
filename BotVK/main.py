import telebot as telebot
from vk_api import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import telebot
from config import logger, telegram_chat_id, telegram_bot_token, group_token, group_id
import os
from wget import download


def get_cache_dir():
    path = '.cache'

    if os.path.exists(path):
        return os.path.abspath(path)
    else:
        try:
            os.mkdir(path)
            return os.path.abspath(path)
        except OSError as _ex:
            logger.error(f"Создать директорию {path} не удалось. {_ex}")
            return ''


cache_dir = get_cache_dir()

vk_link = 'https://vk.com/'

t_bot = telebot.TeleBot(telegram_bot_token, parse_mode='HTML')

vk = vk_api.VkApi(token=group_token)
longpoll = VkBotLongPoll(vk, group_id)
vk = vk.get_api()


# https://github.com/qwertyadrian/TG_AutoPoster/blob/master/TG_AutoPoster/sender.py


class Post:
    post_id = None
    text = ''
    photo = []
    video = []
    # docs = []
    user_id = None
    user_info = None
    date = None
    post_type = None
    owner_id = None
    link = ''

    def __init__(self):
        self.post_id = None
        self.text = ''
        self.photo = []
        self.video = []
        # self.docs = []
        self.user_id = None
        self.user_info = None
        self.date = None
        self.post_type = None
        self.owner_id = None
        self.link = ''

    def pars_wall_post(self, wall_post):
        if wall_post.type == VkBotEventType.WALL_POST_NEW:
            self.text = wall_post.object['text']
            self.user_id = wall_post.object['from_id']
            self.user_info = get_user_info(self.user_id)
            self.date = wall_post.object['date']
            self.post_type = wall_post.object['post_type']
            self.post_id = wall_post.object['id']
            self.owner_id = wall_post.object['owner_id']
            if self.owner_id is not None and self.post_id is not None:
                self.link = f'{vk_link}wall{self.owner_id}_{self.post_id}'
            for attachment in wall_post.object.get('attachments', []):
                attachment_type = attachment.get('type')
                if attachment_type == 'photo':
                    sizes = attachment.get('photo', {}).get('sizes', [])
                    if len(sizes) > 0:
                        max_size = sizes[-1]
                        try:
                            photo = download(max_size['url'], out=cache_dir)
                            photo = photo.replace('/', '\\')
                        except Exception as _ex:
                            photo = None
                            logger.error(f'Ошибка при загрузки фото: \n{attachment} \n{_ex}')
                        if photo:
                            self.photo.append(photo)
                            # with open(photo, 'rb') as photo_file:
                            #     self.photo.append(photo_file)
                            # os.remove(photo)

        # @logger.catch()


def get_user_info(user_id):
    user_info = {
        'id': user_id,
        'url': f'{vk_link}id{user_id}',
        'name': '',
        'first_name': '',
        'last_name': '',
        'photo_max': '',
        'last_seen': '',
        'city': '',
        'can_write_private_message': False,
        'online': False,
        'sex': '',
        'chat_name': f'[id{user_id}]',
        'user_info_is_found': False
    }
    try:
        fields = 'id, first_name,last_name, photo_max, last_seen, city, can_write_private_message, online, sex'
        response = vk.users.get(user_ids=user_id, fields=fields)
        if isinstance(response, list) and len(response) > 0:
            user_info.update(response[0])
            city = user_info['city']
            user_info['city'] = city.get('title', '') if isinstance(city, dict) else city
            sex = user_info.get('sex', 0)
            user_info['sex'] = 'female' if sex == 1 else 'male' if sex == 2 else ''
            user_info['name'] = '{} {}'.format(user_info.get('last_name', ''), user_info.get('first_name', ''))
            user_info['chat_name'] = '[id{}|{}]'.format(user_id, user_info.get('name', ''))
            user_info['online'] = bool(user_info.get('online', 0))
            user_info['can_write_private_message'] = bool(user_info.get('can_write_private_message', 0))
            user_info['user_info_is_found'] = True
    except Exception as _ex:
        print("Ошибка получения информации о пользователе: {0}".format(_ex))
    return user_info


# @logger.catch()
def send_post(post: Post):
    count_of_media = len(post.photo) + len(post.video)

    images = [(lambda f: telebot.types.InputMediaPhoto(open(f, 'rb')))(f) for f in post.photo]
    video = [(lambda f: telebot.types.InputMediaVideo(open(f, 'rb')))(f) for f in post.video]

    media = []
    media.extend(images)
    media.extend(video)

    user_name = post.user_info.get('name')
    user_url = post.user_info.get('url')
    mes_text = f'Новый пост от пользователя <a href="{user_url}">{user_name}</a>:\n{post.text}'

    media_messages = []

    if len(media) > 1:
        media_message = t_bot.send_media_group(
            chat_id=telegram_chat_id,
            media=media,
            disable_notification=True
        )
        media_messages.append(media_message)
    else:
        if len(images) == 1:
            media_message = t_bot.send_photo(
                chat_id=telegram_chat_id,
                photo=images[0]
            )
            media_messages.append(media_message)
            # media.remove(images[0])
        if len(video) == 1:
            media_message = t_bot.send_video(
                chat_id=telegram_chat_id,
                video=video[0]
            )
            media_messages.append(media_message)
            # media.remove(video[0])

    text_message = t_bot.send_message(
        chat_id=telegram_chat_id,
        text=mes_text
    )

    return text_message, media_messages


try:
    for event in longpoll.listen():

        if event.type == VkBotEventType.WALL_POST_NEW:
            new_post = Post()
            new_post.pars_wall_post(event)
            send_post(new_post)

except Exception as ex:
    logger.error(ex)
