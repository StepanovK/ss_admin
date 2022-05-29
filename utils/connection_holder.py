from utils.singleton import Singleton
from vk_api import vk_api
import utils.config as config


class VKConnectionsHolder(metaclass=Singleton):
    def __init__(self):
        self._vk_api_group = None
        self._vk_connection_group = None
        self._vk_api_admin = None
        self._vk_connection_admin = None

    @staticmethod
    def close():
        if VKConnectionsHolder.instance._vk_connection_group:
            VKConnectionsHolder.instance._vk_connection_group = None
        if VKConnectionsHolder.instance._vk_connection_admin:
            VKConnectionsHolder.instance._vk_connection_admin = None

        config.logger.info("Connections closed")

    @property
    def vk_api_group(self):
        if not self._vk_api_group:
            try:
                self._vk_api_group = vk_api.VkApi(token=config.group_token)
                config.logger.info("Init VK api for group")
            except Exception as ex:
                config.logger.error(f"Failed to init VK api for group: {ex}")
        return self._vk_api_group

    @property
    def vk_connection_group(self):
        if not self._vk_connection_group and self.vk_api_group:
            try:
                self._vk_connection_group = self.vk_api_group.get_api()
                config.logger.info("Init VK group client")
            except Exception as ex:
                config.logger.error(f"Failed to init VK group client: {ex}")
        return self._vk_connection_group

    @property
    def vk_api_admin(self):
        if not self._vk_api_admin:
            try:
                self._vk_api_admin = vk_api.VkApi(login=config.admin_phone,
                                                  password=config.admin_pass,
                                                  token=config.admin_token)
                config.logger.info("Init VK api for group")
            except Exception as ex:
                config.logger.error(f"Failed to init VK api for group: {ex}")
        return self._vk_api_admin

    @property
    def vk_connection_admin(self):
        if not self._vk_connection_admin and self._vk_api_admin:
            try:
                self._vk_connection_admin = self._vk_api_admin.get_api()
                config.logger.info("Init VK admin client")
            except Exception as ex:
                config.logger.error(f"Failed to init VK admin client: {ex}")
        return self._vk_connection_admin
