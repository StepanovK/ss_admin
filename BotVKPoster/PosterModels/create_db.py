from config import logger
from .base import db
from .MessagesOfSuggestedPosts import MessageOfSuggestedPost
from .PublishedPosts import PublishedPost
from .SortedHashtags import SortedHashtag


def create_all_tables():
    models = [
        MessageOfSuggestedPost,
        PublishedPost,
        SortedHashtag,
    ]

    with db:
        db.create_tables(models)


if __name__ == '__main__':
    logger.info('Обновление базы данных:')

    logger.info(' - Создание таблиц. Начало')
    create_all_tables()
    logger.info(' - Создание таблиц. Конец')
