import datetime

from Models.ChatMessages import ChatMessage
from Models.Chats import Chat
from Models.Users import User
from . import users
from . import attachments
from config import logger


def parse_chat_message(vk_object: dict, vk_connection=None, chat=None, owner_id=0):
    if chat is None:
        chat_id = vk_object.get('peer_id')
        chat_full_id = Chat.generate_id(owner_id=owner_id, chat_id=chat_id)
        chat, created = Chat.get_or_create(id=chat_full_id,
                                           owner_id=owner_id,
                                           chat_id=chat_id)
    if 'reply_message' in vk_object:
        replied_message = parse_chat_message(vk_object=vk_object['reply_message'],
                                             vk_connection=vk_connection,
                                             chat=chat,
                                             owner_id=owner_id)
    else:
        replied_message = None
    mes_id = vk_object.get('conversation_message_id')
    message_id = ChatMessage.generate_id(message_id=mes_id, chat=chat)
    message, created = ChatMessage.get_or_create(id=message_id,
                                                 message_id=mes_id,
                                                 chat=chat)
    message.replied_message = replied_message
    message.text = vk_object.get('text', '')
    from_id = vk_object.get('from_id', 0)
    if from_id > 0:
        message.user = users.get_or_create_user(from_id, vk_connection)
    else:
        message.from_group = True
    message.date = datetime.datetime.fromtimestamp(vk_object.get('date'))

    message.save()

    attachments.parce_added_attachments(attachment_object=message,
                                        attachments=vk_object.get('attachments', []),
                                        user=message.user)
    return message
