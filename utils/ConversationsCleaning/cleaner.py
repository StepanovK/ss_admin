import datetime

from config import logger
from conversation_settings import get_conversation_settings, default_conv_settings
from Models.Conversations import Conversation
from Models.ConversationMessages import ConversationMessage
from Models.Users import User
from utils.connection_holder import ConnectionsHolder


def start_cleaning():
    logger.info('Conversation cleaning started')

    now_time = datetime.datetime.now()

    conversation_settings = get_conversation_settings()

    for conversation in Conversation.select().where(Conversation.days_for_cleaning > 0):

        settings = conversation_settings.get(conversation.conversation_id)
        if settings is None:
            settings = default_conv_settings()

        for conv_message in ConversationMessage.select().where(
                (ConversationMessage.conversation == conversation)
                & (ConversationMessage.is_deleted == False)
                & (ConversationMessage.user.is_null(False))).join(User).order_by(ConversationMessage.date):

            comment_days = settings['comments_settings'].get(conv_message.message_id)
            user_days = settings['users_settings'].get(conv_message.user.id)

            if comment_days is not None:
                days_for_cleaning = comment_days
            elif user_days is not None:
                days_for_cleaning = user_days
            else:
                days_for_cleaning = conversation.days_for_cleaning

            if days_for_cleaning == 0:
                continue

            date_for_cleaning = now_time - datetime.timedelta(days=days_for_cleaning)

            if conv_message.date <= date_for_cleaning:
                remove_conversation_message(conversation, conv_message)

    logger.info('Conversation cleaning finished')


def remove_conversation_message(conversation: Conversation, conversation_message: ConversationMessage):
    vk_connection = ConnectionsHolder().vk_connection_admin

    try:
        result = vk_connection.board.deleteComment(group_id=-conversation.owner_id,
                                                   topic_id=conversation.conversation_id,
                                                   comment_id=conversation_message.message_id)
    except Exception as ex:
        result = ex
        logger.error(f'Failed to delete conversation message {conversation_message}: {ex}')

    if result == 1:
        conversation_message.is_deleted = True
        conversation_message.save()
        print(f'Коммент от {conversation_message.date} удалён {conversation_message}')
    else:
        print(f'При удалении коммента {conversation_message} возникла ошибка: {result}')


if __name__ == '__main__':
    start_cleaning()
