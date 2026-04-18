import random

import pika

from utils.singleton import Singleton
from vk_api import vk_api
import config as config


class ConnectionsHolder(metaclass=Singleton):
    def __init__(self):
        self.vk_group_token = config.group_token
        self._vk_api_group = None
        self._vk_connection_group = None
        self._vk_api_admin = None
        self._vk_connection_admin = None
        self._rabbit_connection = None
        self._token_expiry_warning_sent = None

    @staticmethod
    def close():
        ConnectionsHolder.close_vk_connections()
        ConnectionsHolder.close_rabbit_connection()
        if config.debug:
            config.logger.info("Connections closed")

    @staticmethod
    def close_rabbit_connection():
        if ConnectionsHolder.instance:
            if ConnectionsHolder.instance._rabbit_connection:
                ConnectionsHolder.instance._rabbit_connection.close()
                ConnectionsHolder.instance._rabbit_connection = None

    @staticmethod
    def close_vk_connections():
        if ConnectionsHolder.instance:
            if ConnectionsHolder.instance._vk_connection_group:
                ConnectionsHolder.instance._vk_connection_group = None
                if config.debug:
                    config.logger.info("vk_connection_group closed")
            if ConnectionsHolder.instance._vk_connection_admin:
                ConnectionsHolder.instance._vk_connection_admin = None
                if config.debug:
                    config.logger.info("vk_connection_admin closed")

    def _init_token_from_db(self):
        """Инициализирует токен из БД или .env при первом запуске"""
        if self._token_initialized:
            return

        try:
            from Models.AppTokens import AppToken
            token_record = AppToken.init_from_env()
            self._token_initialized = True

            if token_record:
                config.logger.info(f"Token initialized. Expires at: {token_record.expires_at}")
            else:
                config.logger.warning("No token available!")
        except Exception as ex:
            config.logger.error(f"Failed to initialize token: {ex}")
            self._token_initialized = True  # Чтобы не пытаться снова

    def _get_current_access_token(self):
        """Получает актуальный токен из БД"""
        try:
            from Models.AppTokens import AppToken
            token_record = AppToken.get_master_token()

            if token_record:
                # Проверяем, не истёк ли токен
                if token_record.is_expired(buffer_minutes=5):
                    seconds_left = token_record.seconds_until_expiry()
                    if not self._token_expiry_warning_sent and seconds_left < 300:  # 5 минут
                        self._send_token_warning(seconds_left)

                    if seconds_left <= 0:
                        config.logger.error("Token has expired! Please update ADMIN_ACCESS_TOKEN in .env")
                        return None

                return token_record.access_token
            else:
                config.logger.error("No token record found in database!")
                return None

        except Exception as ex:
            config.logger.error(f"Failed to get token from DB: {ex}")
            return None

    def _send_token_warning(self, seconds_left):
        """Отправляет предупреждение об истекающем токене"""
        try:
            self._token_expiry_warning_sent = True
            config.logger.warning(f"Token expires in {seconds_left:.0f} seconds!")

            # Пытаемся отправить в healthcheck-чат
            if self.vk_connection_group:
                self.vk_connection_group.messages.send(
                    peer_id=config.healthcheck_chat_id,
                    message=f'⚠️ ВНИМАНИЕ! Токен администратора истекает через {seconds_left:.0f} сек.\n\n'
                            f'Обновите ADMIN_ACCESS_TOKEN в .env файле и перезапустите бота.',
                    random_id=random.randint(10 ** 5, 10 ** 6)
                )
        except Exception as ex:
            config.logger.error(f"Failed to send token warning: {ex}")

    @property
    def vk_api_group(self):
        if not self._vk_api_group:
            try:
                self._vk_api_group = vk_api.VkApi(token=self.vk_group_token)
                if config.debug:
                    config.logger.info("Init VK api for group")
            except Exception as ex:
                config.logger.error(f"Failed to init VK api for group: {ex}")
        return self._vk_api_group

    @property
    def vk_connection_group(self):
        if not self._vk_connection_group and self.vk_api_group:
            try:
                self._vk_connection_group = self.vk_api_group.get_api()
                if config.debug:
                    config.logger.info("Init VK group client")
            except Exception as ex:
                config.logger.error(f"Failed to init VK group client: {ex}")
        return self._vk_connection_group

    @property
    def vk_api_admin(self):
        """Получает актуальный токен админа из БД перед созданием подключения"""
        if not self._vk_api_admin:
            # Инициализируем токен при первом обращении
            self._init_token_from_db()

            access_token = self._get_current_access_token()

            if access_token:
                try:
                    self._vk_api_admin = vk_api.VkApi(token=access_token)
                    self._token_expiry_warning_sent = False
                    if config.debug:
                        config.logger.info("Init VK api for admin with token from DB")
                except Exception as ex:
                    config.logger.error(f"Failed to init VK api for admin: {ex}")
            else:
                config.logger.error("No valid access token available for admin API!")

        return self._vk_api_admin

    @property
    def vk_connection_admin(self):
        if not self._vk_connection_admin and self.vk_api_admin:
            try:
                self._vk_connection_admin = self.vk_api_admin.get_api()
                if config.debug:
                    config.logger.info("Init VK admin client")
            except Exception as ex:
                config.logger.error(f"Failed to init VK admin client: {ex}")
        return self._vk_connection_admin

    def refresh_admin_connection(self):
        """Принудительно обновляет подключение админа (например, после обновления токена)"""
        config.logger.info("Refreshing admin connection...")
        self._vk_api_admin = None
        self._vk_connection_admin = None
        self._token_expiry_warning_sent = False
        # Принудительно создаём заново
        _ = self.vk_api_admin
        _ = self.vk_connection_admin

    @property
    def rabbit_connection(self):
        if self._rabbit_connection is not None and self._rabbit_connection.is_closed:
            self._rabbit_connection = None

        if self._rabbit_connection is None:
            self._rabbit_connection = RabbitConnector.get_new_rabbit_connection()

        return self._rabbit_connection


class RabbitConnector:

    @classmethod
    def get_or_reconnect_rabbit(cls, rabbit_connection=None):
        if rabbit_connection is not None and rabbit_connection.is_closed:
            rabbit_connection = None

        if rabbit_connection is None:
            rabbit_connection = cls.get_new_rabbit_connection()

        return rabbit_connection

    @classmethod
    def get_new_rabbit_connection(cls):
        rabbit_connection = None
        try:
            credentials = pika.PlainCredentials('guest', 'guest')
            conn_params = pika.ConnectionParameters(host=config.rabbitmq_host,
                                                    port=config.rabbitmq_port,
                                                    credentials=credentials)
            try:
                rabbit_connection = pika.BlockingConnection(conn_params)
            except pika.exceptions.AMQPConnectionError:
                config.logger.warning(
                    f'failed to connect to rabbitmq! ({config.rabbitmq_host}:{config.rabbitmq_port})')
        except Exception as ex:
            config.logger.error(f"Failed to init rabbitmq client: {ex}")

        return rabbit_connection
