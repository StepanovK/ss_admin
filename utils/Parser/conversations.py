import datetime

from Models.ConversationMessages import ConversationMessage
from Models.Conversations import Conversation
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
        conversation, created = Conversation.get_or_create(id=conversation_id,
                                                           owner_id=owner_id,
                                                           conversation_id=topic_id)
        if created and vk_connection is not None:
            topics = vk_connection.board.getTopics(group_id=-owner_id,
                                                   topic_ids=str(topic_id),
                                                   preview=1)['items']
            if len(topics) > 0:
                parse_conversation(vk_object=topics[0], owner_id=owner_id, vk_connection=vk_connection)
    else:
        owner_id = conversation.owner_id
        topic_id = conversation.conversation_id
    mes_id = vk_object.get('id')
    message_id = ConversationMessage.generate_id(owner_id=owner_id,
                                                 conversation_id=topic_id,
                                                 message_id=mes_id)
    conv_mes, created = ConversationMessage.get_or_create(id=message_id,
                                                          message_id=mes_id,
                                                          conversation=conversation)
    conv_mes.text = vk_object.get('text', '')
    conv_mes.is_edited = vk_object.get('is_edited', False)
    conv_mes.date = datetime.datetime.fromtimestamp(vk_object.get('date'))
    user_id = vk_object.get('from_id', 0)
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
    message_id = ConversationMessage.generate_id(owner_id=owner_id,
                                                 conversation_id=topic_id,
                                                 message_id=mes_id)
    conv = get_conversation(owner_id, topic_id)
    if conv is None:
        logger.warning(f'Can`t update the conversation`s message id={message_id}')
        return None

    conv_mes, created = ConversationMessage.get_or_create(id=message_id,
                                                          conversation=conv)
    conv_mes.is_deleted = True

    conv_mes.save()

    attachments.mark_attachments_as_deleted(attachment_object=conv_mes)

    return conv_mes


def parse_undelete_conversation_message(vk_object: dict):
    owner_id = vk_object.get('topic_owner_id')
    topic_id = vk_object.get('topic_id')
    mes_id = vk_object.get('id')
    message_id = ConversationMessage.generate_id(owner_id=owner_id,
                                                 conversation_id=topic_id,
                                                 message_id=mes_id)
    conv = get_conversation(owner_id, topic_id)
    if conv is None:
        logger.warning(f'Can`t update the conversation`s message id={message_id}')
        return None

    conv_mes, created = ConversationMessage.get_or_create(id=message_id,
                                                          conversation=conv)
    conv_mes.is_deleted = False

    conv_mes.save()

    attachments.mark_attachments_as_undeleted(attachment_object=conv_mes)

    return conv_mes


def get_conversation(owner_id, topic_id):
    conv_id = Conversation.generate_id(owner_id=owner_id, conversation_id=topic_id)
    try:
        return Conversation.get(id=conv_id)
    except Conversation.DoesNotExist:
        logger.warning(f'Can`t get conversation by id={conv_id}')
        return None
