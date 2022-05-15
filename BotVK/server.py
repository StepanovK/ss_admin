import config
from config import logger
from vk_api import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from time import sleep

from Parser import comments, likes, posts, subscriptions


class Server:
    vk_link = 'https://vk.com/'

    def __init__(self,
                 vk_group_token: str,
                 admin_token: str,
                 admin_phone: str,
                 admin_pass: str,
                 vk_group_id: int
                 ):
        self.group_token = vk_group_token
        self.group_id = vk_group_id
        self.admin_token = admin_token
        self.admin_phone = admin_phone
        self.admin_pass = admin_pass
        self.vk_api = None
        self.vk_connection = None
        self.vk_api_admin = None
        self.vk_connection_admin = None
        self._longpoll = None
        self._connect_vk()
        self._connect_vk_admin()

    def _connect_vk(self):
        try:
            self.vk_api = vk_api.VkApi(token=self.group_token)
            self.vk_connection = self.vk_api.get_api()
        except Exception as err:
            logger.error(f'Не удалось подключиться к ВК по причине: {err}')

    def _connect_vk_admin(self):
        try:
            self.vk_api_admin = vk_api.VkApi(
                login=self.admin_phone,
                password=self.admin_pass,
                token=self.admin_token)
            self.vk_connection_admin = self.vk_api_admin.get_api()
        except Exception as err:
            logger.error(f'Не удалось подключиться к ВК под админом по причине: {err}')

    def _start_polling(self):
        if self.vk_connection is None:
            self._connect_vk()
        self._longpoll = VkBotLongPoll(self.vk_api, self.group_id, )

        logger.info('Бот запущен')

        for event in self._longpoll.listen():

            logger.info(f'Новое событие {event.type}')
            if event.type == VkBotEventType.WALL_POST_NEW:
                new_post = posts.parse_wall_post(event.object, self.vk_connection_admin)
                str_from_user = '' if new_post.user is None else f'от {new_post.user} '
                str_attachments = '' if len(new_post.attachments) == 0 else f', вложений: {len(new_post.attachments)}'
                str_action = 'Опубликован пост' if new_post.suggest_status is None else 'В предложке новый пост'
                logger.info(f'{str_action} {str_from_user}{new_post}{str_attachments}')
            elif event.type == 'like_add':
                likes.parse_like_add(event.object, self.vk_connection_admin)
            elif event.type == 'like_remove':
                likes.parse_like_remove(event.object, self.vk_connection_admin)
            elif event.type == VkBotEventType.WALL_REPLY_NEW:
                comments.parse_comment(event.object, self.vk_connection_admin)
            elif event.type == VkBotEventType.WALL_REPLY_DELETE:
                comments.parse_delete_comment(event.object, self.vk_connection_admin)
            elif event.type == VkBotEventType.WALL_REPLY_RESTORE:
                comments.parse_restore_comment(event.object, self.vk_connection_admin)
            elif event.type == VkBotEventType.GROUP_JOIN:
                subscriptions.parse_subscription(event, self.vk_connection_admin, True)
            elif event.type == VkBotEventType.GROUP_LEAVE:
                subscriptions.parse_subscription(event, self.vk_connection_admin, False)

    def run(self):
        # try:
        self._start_polling()
        # except Exception as ex:
        #     logger.error(ex)

    def run_in_loop(self):
        while True:
            self.run()
            sleep(60)


if __name__ == '__main__':
    server = Server(vk_group_token=config.group_token,
                    admin_token=config.admin_token,
                    admin_phone=config.admin_phone,
                    admin_pass=config.admin_pass,
                    vk_group_id=config.group_id)
    server.run_in_loop()
