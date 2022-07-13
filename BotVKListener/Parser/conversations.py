import datetime

from Models.ConversationsMessages import ConversationsMessage
from Models.Conversations import Conversation
from Models.Users import User
from . import users
from . import attachments
from config import logger


def parse_conversation(vk_object: dict, owner_id: int, vk_connection=None):
    topic_id = vk_object.get('id')
    conversation_id = Conversation.generate_id(owner_id=owner_id, conversation_id=topic_id)
    conversation, _ = Conversation.get_or_create(id=conversation_id,
                                                 owner_id=owner_id,
                                                 conversation_id=topic_id)
    conversation.title = vk_object.get('title', '')
    conversation.is_closed = bool(vk_object.get('is_closed', 0))
    conversation.text = vk_object.get('first_comment', '')
    conversation.date_of_creating = datetime.date.fromtimestamp(vk_object.get('created',
                                                                              datetime.date.today()))
    conversation.save()

    return conversation


def parse_conversation_message(vk_object: dict, vk_connection=None, is_edited=False, conversation=None):
    if conversation is None:
        owner_id = vk_object.get('topic_owner_id')
        topic_id = vk_object.get('topic_id')
        conversation_id = Conversation.generate_id(owner_id=owner_id, conversation_id=topic_id)
        conversation, _ = Conversation.get_or_create(id=conversation_id,
                                                     owner_id=owner_id,
                                                     conversation_id=topic_id)
    else:
        owner_id = conversation.owner_id
        topic_id = conversation.conversation_id
    mes_id = vk_object.get('id')
    message_id = ConversationsMessage.generate_id(owner_id=owner_id,
                                                  conversation_id=topic_id,
                                                  message_id=mes_id)
    conv_mes, created = ConversationsMessage.get_or_create(id=message_id,
                                                           message_id=mes_id,
                                                           conversation=conversation)
    conv_mes.text = vk_object.get('text', '')
    user_id = vk_object.get('from_id', 0)
    is_edited = is_edited
    conv_mes.date = datetime.datetime.fromtimestamp(vk_object.get('date'))
    if user_id > 0:
        conv_mes.user = users.get_or_create_user(user_id, vk_connection)
    elif user_id < 0:
        conv_mes.from_group = True

    conv_mes.save()

    attachments.parce_added_attachments(attachment_object=conv_mes,
                                        attachments=vk_object.get('attachments', []),
                                        user=conv_mes.user)
    return conv_mes


def parse_delete_conversation_message(vk_object: dict):
    owner_id = vk_object.get('topic_owner_id')
    topic_id = vk_object.get('topic_id')
    mes_id = vk_object.get('id')
    message_id = ConversationsMessage.generate_id(owner_id=owner_id,
                                                  conversation_id=topic_id,
                                                  message_id=mes_id)
    conv_mes, created = ConversationsMessage.get_or_create(id=message_id)
    conv_mes.is_deleted = True

    conv_mes.save()

    attachments.mark_attachments_as_deleted(attachment_object=conv_mes)

    return conv_mes
