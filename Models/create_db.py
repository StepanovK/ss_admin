import config as config
import psycopg2
import psycopg2.extras
import os
from config import logger
from Models.base import db
from Models.Admins import Admin
from Models.UploadedFiles import UploadedFile
from Models.Comments import Comment
from Models.Posts import Post, PostsHashtag
from Models.PrivateMessages import PrivateMessage
from Models.Relations import CommentsAttachment, CommentsLike, PostsAttachment, PostsLike, PrivateMessageAttachment
from Models.Subscriptions import Subscription
from Models.Users import User

LOCK_FILE_NAME = 'lock_db'


def create_all_tables():
    models = [
        Admin,
        User,
        UploadedFile,
        Post,
        PostsHashtag,
        PostsAttachment,
        PostsLike,
        Comment,
        CommentsAttachment,
        CommentsLike,
        Subscription,
        PrivateMessage,
        PrivateMessageAttachment,
    ]
    with db:
        db.create_tables(models)


def get_pg_connection():
    try:
        connection = psycopg2.connect(
            host=config.db_host,
            port=config.db_port,
            user=config.db_user,
            password=config.db_password
        )
        return connection
    except Exception as ex:
        connection_info = f'host={config.db_host}, port={config.db_port},' \
                          f' user={config.db_user} password={config.db_password}'
        logger.error(f"Проблема при подключении к PostgreSQL\n({connection_info}):", ex)
        return None


def delete_database():
    conn = get_pg_connection()
    conn.autocommit = True
    with conn.cursor() as cursor:
        try:
            cursor.execute(
                f"""DROP DATABASE IF EXISTS {config.db_name};"""
            )
        except Exception as ex:
            logger.error(f'Не удалось удалить базу данных.\n{ex}')
    conn.close()


def create_database():
    if db_is_locked():
        logger.warning('Database is locked!')
        return

    conn = get_pg_connection()
    conn.autocommit = True
    with conn.cursor() as cursor:
        try:
            cursor.execute(
                f"""CREATE DATABASE {config.db_name}
                    WITH 
                    OWNER = postgres
                    ENCODING = 'UTF8'
                    TABLESPACE = pg_default
                    CONNECTION LIMIT = -1;"""
            )
        except Exception as ex:
            logger.error(f'Не удалось создать базу данных.\n{ex}')
    conn.close()


def recreate_database():
    if db_is_locked():
        logger.warning('Database is locked!')
        return

    logger.info('Обновление базы данных:')

    logger.info('1 - Удаление БД. Начало')
    delete_database()
    logger.info('1 - Удаление БД. Конец')

    logger.info('2 - Создание БД. Начало')
    create_database()
    logger.info('2 - Создание БД. Конец')

    logger.info('3 - Создание таблиц. Начало')
    create_all_tables()
    logger.info('3 - Создание таблиц. Конец')

    lock_db()


def lock_db():
    try:
        with open(LOCK_FILE_NAME, 'w+') as lock_file:
            lock_file.close()
            logger.info('Database was locked.')
    except FileNotFoundError:
        pass


def unlock_db():
    if os.path.exists(LOCK_FILE_NAME):
        try:
            os.remove(LOCK_FILE_NAME)
            logger.warning('Database is unlocked.')
        except Exception as ex:
            logger.error(f'Can`t unlock database: {ex}')


def db_is_locked():
    return os.path.exists(LOCK_FILE_NAME)


if __name__ == '__main__':
    recreate_database()
