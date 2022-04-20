from vk_api import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import telebot
from config import logger, telegram_chat_id, telegram_bot_token, group_token, group_id

t_bot = telebot.TeleBot('telebot')
t_bot.config['api_key'] = telegram_bot_token

vk = vk_api.VkApi(token=group_token)
vk._auth_token()
vk.get_api()
longpoll = VkBotLongPoll(vk, group_id)


def upload_photos(photos):
    if len(photos):
        t_bot.send_photo()



def send_msg(text):
    t_bot.send_message(chat_id=telegram_chat_id, text=text)



try:
    for event in longpoll.listen():
        if event.type == VkBotEventType.WALL_POST_NEW:
            photos = []
            text = event.object['text']  # text from Vk post
            if 'attachments' not in str(event):
                send_msg(text)
            else:
                for attachment in event.object['attachments']:
                    if attachment['type'] == 'photo':
                        pass
                    else:
                        pass
                upload_photos(photos)
                photos.clear()
            send_msg(text)

except Exception as ex:
    logger.error(ex)
