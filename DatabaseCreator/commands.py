import config
import argparse
import psycopg2
import psycopg2.extras
from config import logger

parser = argparse.ArgumentParser(description='DatabaseCreator')
parser.add_argument("--resetdb", default=0, help="This is the 'resetdb' variable")


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


def get_bd_connection():
    try:
        connection = psycopg2.connect(
            host=config.db_host,
            port=config.db_port,
            user=config.db_user,
            password=config.db_password,
            database=config.db_name
        )
        return connection
    except Exception as ex:
        connection_info = f'host={config.db_host}, port={config.db_port},' \
                          f' user={config.db_user} password={config.db_password}'
        logger.error(f"Проблема при подключении к базе данных {config.db_name}\n({connection_info}):", ex)
        return None


def reset_database():
    conn = get_pg_connection()
    conn.autocommit = True
    logger.info('Обновление базы данных:')
    with conn.cursor() as cursor:
        logger.info('1 - Удаление БД. Начало')
        cursor.execute(
            f"""DROP DATABASE IF EXISTS {config.db_name};"""
        )
        logger.info('1 - Удаление БД. Конец')

        logger.info('2 - Создание БД. Начало')
        try:
            cursor.execute(
                f"""CREATE DATABASE {config.db_name}
                    WITH 
                    OWNER = postgres
                    ENCODING = 'UTF8'
                    LC_COLLATE = 'Russian_Russia.1251'
                    LC_CTYPE = 'Russian_Russia.1251'
                    TABLESPACE = pg_default
                    CONNECTION LIMIT = -1;"""
            )
            logger.info('2 - Создание БД. Конец')
        except Exception as ex:
            logger.error(f'Не удалось создать базу данных.\n{ex}')
    conn.close()

    with open("database_description.sql", "r") as f:
        sql = f.read()
        conn = get_bd_connection()
        with conn.cursor() as cursor:
            logger.info('3 - Создание таблиц в новой БД. Начало')
            cursor.execute(sql)
            conn.commit()
            logger.info('3 - Создание таблиц в новой БД. Конец')
        conn.close()
    logger.info('База данных создана!')


def add_test_data():
    conn = get_bd_connection()
    with conn.cursor() as cursor:
        with open("test_data.sql", "r") as f:
            sql = f.read()
            cursor.execute(sql)
            conn.commit()
    conn.close()


if __name__ == '__main__':
    args = parser.parse_args()
    if str(args.resetdb) == '1':
        reset_database()
