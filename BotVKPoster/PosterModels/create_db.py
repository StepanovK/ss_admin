from utils.config import logger
from BotVKPoster.PosterModels.base import db
from BotVKPoster.PosterModels.MessagesOfSuggestedPosts import MessageOfSuggestedPost
from BotVKPoster.PosterModels.PublishedPosts import PublishedPost


def create_all_tables():
    models = [
        MessageOfSuggestedPost,
        PublishedPost,
    ]

    with db:
        db.create_tables(models)


if __name__ == '__main__':
    logger.info('Обновление базы данных:')

    logger.info(' - Создание таблиц. Начало')
    create_all_tables()
    logger.info(' - Создание таблиц. Конец')
