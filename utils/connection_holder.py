from utils.singleton import Singleton
from vk_api import vk_api
from utils.config import group_token, admin_token, admin_phone, admin_pass, logger


class ConnectionsHolder(metaclass=Singleton):
    def __init__(self):
        self._vk_client = None
        self._vk_admin_client = None

    @staticmethod
    def close():
        if ConnectionsHolder.instance._vk_client:
            ConnectionsHolder.instance._vk_client = None
        if ConnectionsHolder.instance._vk_admin_client:
            ConnectionsHolder.instance._vk_admin_client = None

        logger.info("Connections closed")

    @property
    def vk_client(self):
        if not self._vk_client:
            try:
                vk_api_ = vk_api.VkApi(token=group_token)
                self._vk_client = vk_api_.get_api()
                logger.info("Init VK client")
            except Exception as ex:
                logger.error(f"Failed to init VK client: {ex}")
        return self._vk_client

    @property
    def vk_admin_client(self):
        if not self._vk_admin_client:
            try:
                vk_api_admin = vk_api.VkApi(
                    login=admin_phone,
                    password=admin_pass,
                    token=admin_token)
                self._vk_admin_client = vk_api_admin.get_api()
                logger.info("Init VK admin client")
            except Exception as ex:
                logger.error(f"Failed to init VK admin client: {ex}")
        return self._vk_admin_client

