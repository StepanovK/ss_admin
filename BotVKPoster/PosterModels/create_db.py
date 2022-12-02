from config import logger
from .base import db
from .MessagesOfSuggestedPosts import MessageOfSuggestedPost
from .PublishedPosts import PublishedPost
from .SortedHashtags import SortedHashtag
from .RepostedToConversationsPosts import RepostedToConversationPost


def create_all_tables():
    models = [
        MessageOfSuggestedPost,
        PublishedPost,
        SortedHashtag,
        RepostedToConversationPost,
    ]

    with db:
        db.create_tables(models)


def check_or_create_db():
    try:
        file = open('input.txt')
    except IOError as e:
        create_all_tables()


if __name__ == '__main__':
    logger.info('Обновление базы данных:')

    logger.info(' - Создание таблиц. Начало')
    create_all_tables()
    logger.info(' - Создание таблиц. Конец')
