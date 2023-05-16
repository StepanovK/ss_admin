import pika

from utils.singleton import Singleton
from vk_api import vk_api
import config as config


class ConnectionsHolder(metaclass=Singleton):
    def __init__(self):
        self.vk_group_token = config.group_token
        self._vk_api_group = None
        # self._vk_api_group_poster = None
        self._vk_connection_group = None
        # self._vk_connection_group_poster = None
        self._vk_api_admin = None
        self._vk_connection_admin = None
        self._rabbit_connection = None

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
                if config.debug:
                    config.logger.info("RabbitMQ connection closed")

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

    # @property
    # def vk_api_group_poster(self):
    #     if not self._vk_api_group_poster:
    #         try:
    #             self._vk_api_group_poster = vk_api.VkApi(token=config.group_token_2)
    #             if config.debug:
    #                 config.logger.info("Init VK api for group")
    #         except Exception as ex:
    #             config.logger.error(f"Failed to init VK api for group: {ex}")
    #     return self._vk_api_group_poster

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

    # @property
    # def vk_connection_group_poster(self):
    #     if not self._vk_connection_group_poster and self.vk_api_group:
    #         try:
    #             self._vk_connection_group_poster = self.vk_api_group.get_api()
    #             if config.debug:
    #                 config.logger.info("Init VK group client")
    #         except Exception as ex:
    #             config.logger.error(f"Failed to init VK group client: {ex}")
    #     return self._vk_connection_group_poster

    @property
    def vk_api_admin(self):
        if not self._vk_api_admin:
            try:
                self._vk_api_admin = vk_api.VkApi(token=config.admin_token)
                if config.debug:
                    config.logger.info("Init VK api for group")
            except Exception as ex:
                config.logger.error(f"Failed to init VK api for group by token: {ex}")
        if not self._vk_api_admin:
            try:
                self._vk_api_admin = vk_api.VkApi(login=config.admin_phone,
                                                  password=config.admin_pass,
                                                  token=config.admin_token)
                if config.debug:
                    config.logger.info("Init VK api for group")
            except Exception as ex:
                config.logger.error(f"Failed to init VK api for group by pass: {ex}")
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
                if config.debug:
                    config.logger.info("Init RabbitMQ connection")
            except pika.exceptions.AMQPConnectionError:
                config.logger.warning(
                    f'failed to connect to rabbitmq! ({config.rabbitmq_host}:{config.rabbitmq_port})')
        except Exception as ex:
            config.logger.error(f"Failed to init rabbitmq client: {ex}")

        return rabbit_connection
