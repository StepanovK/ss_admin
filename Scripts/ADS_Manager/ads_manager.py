import re
from datetime import datetime, timedelta, date
from utils.config import group_id, logger, spreadsheetId
from utils.googleSheetsManager import GoogleSheetsManager
from utils.connection_holder import ConnectionsHolder


class ADSPost:
    def __init__(self):
        self.post_id: int = None
        self.date_public: date = None
        self.date_pin: date = None
        self.date_unpin: date = None
        self.date_del: date = None
        self.is_firm: bool = False
        self.out_of_order: bool = False
        self.author: str = None
        self.is_picture: bool = False
        self.post_link: str = None
        self.theme: str = None
        self.price: str = None
        self.extra_tariff: bool = False
        self.who_posted: str = None
        self.is_deleted: bool = False
        self._vk = ConnectionsHolder().vk_admin_client
        self._group_id = group_id

    def take_data_from_dict(self, data_dict):
        if data_dict.get('Ссылка на пост') and re.search(r'\d+_(\d+\b)', data_dict.get('Ссылка на пост')):
            self.post_id = int(re.search(r'\d+_(\d+\b)', data_dict.get('Ссылка на пост')).group(1))
        if self.post_id is None:
            return False
        self.post_link = data_dict.get('Ссылка на пост')
        self.date_public: datetime = data_dict.get('Дата размещения')
        self.date_pin: datetime = data_dict.get('Дата закрепления')
        self.date_unpin: datetime = data_dict.get('Дата открепления')
        self.date_del: datetime = data_dict.get('Дата удаления')
        self.is_firm: bool = data_dict.get('Фирмы', self.is_firm)
        self.out_of_order: bool = data_dict.get('Вне очереди', self.out_of_order)
        self.author: str = data_dict.get('Рекламодатель', self.author)
        self.is_picture: bool = data_dict.get('Наличие фото', self.is_picture)
        self.theme: str = data_dict.get('Тематика', self.theme)
        self.price: str = data_dict.get('Сумма', self.price)
        self.extra_tariff: bool = data_dict.get('Повышенный тариф', self.extra_tariff)
        self.who_posted: str = data_dict.get('Кто запостил', self.who_posted)
        return self

    def pin_wall_post(self):
        try:
            self._vk.wall.pin(owner_id=f"-{group_id}", post_id=self.post_id)
            logger.info(f'OK! post id - {self.post_id} was pined')
        except self._vk.exceptions.ApiError as err:
            logger.error(f"ApiError: {err}, post id - {self.post_id} wasn't pined")

    def unpin_wall_post(self):
        try:
            self._vk.wall.unpin(owner_id=f"-{group_id}", post_id=self.post_id)
            logger.info(f'OK! post id - {self.post_id} was unpined')
        except self._vk.exceptions.ApiError as err:
            logger.error(f"ApiError: {err}, post id - {self.post_id} wasn't unpined")

    def del_wall_post(self):
        try:
            self._vk.wall.delete(owner_id=f"-{group_id}", post_id=self.post_id)
            logger.info(f'OK! post id - {self.post_id} was deleted')
        except self._vk.exceptions.ApiError as err:
            logger.error(f"ApiError: {err}, post id - {self.post_id} wasn't deleted")

    def find_wall_post(self):
        try:
            if self._vk.wall.getById(posts=f"-{self._group_id}_{self.post_id}"):
                return self._vk.wall.getById(posts=f"-{self._group_id}_{self.post_id}")[0]
            else:
                posts = self._vk.wall.get(owner_id=f"-{self._group_id}")
                count = posts.get("count")
                offset = 0
                while offset < 200:
                    posts = self._vk.wall.get(owner_id=f"-{self._group_id}", count=100, offset=offset)
                    for post in posts['items']:
                        if 'postponed_id' in post:
                            if post['postponed_id'] == self.post_id:
                                self.post_id = post["id"]
                                # result_ = self._vk.wall.getById(posts=f"-{self._group_id}_{self.post_id}")
                                return self._vk.wall.getById(posts=f"-{self._group_id}_{self.post_id}")[0]
                    offset += 100
        except Exception as err:
            logger.error(f"ApiError: {err}")
        return False

    def __repr__(self):
        return f"ADSPost({self.__dict__})"


class ADSManager:
    def __init__(self):
        self._google_sheet = GoogleSheetsManager(spreadsheetId)
        self.sheet_posts = []
        self.__get_ads_posts()
        self.date_delta = datetime.date(datetime.now()) - timedelta(30)  #

    def __get_ads_posts(self):
        raw_ads_posts = self._google_sheet.get_sheet_values("Реклама")
        for raw_post in raw_ads_posts:
            raw_response = self._google_sheet.take_data_from_raw_dict(raw_post)
            response = ADSPost().take_data_from_dict(raw_response)
            if response:
                self.sheet_posts.append(response)

    def control_ads_posts(self):
        for post in self.sheet_posts:
            if isinstance(post.date_public, date):
                if self.date_delta <= post.date_public:
                    current_post = post.find_wall_post()
                    if current_post.get('is_deleted'):
                        continue
                    datetime_post = datetime.fromtimestamp(current_post.get('date'))
                    time_ = datetime_post.time()
                    if isinstance(post.date_del, date):
                        post.date_del = datetime.combine(post.date_del, time_).timestamp()
                        if datetime.now().timestamp() > post.date_del:
                            post.del_wall_post()
                            continue
                    if isinstance(post.date_pin, date) and isinstance(post.date_unpin, date):
                        post.date_pin = datetime.combine(post.date_pin, time_).timestamp()
                        post.date_unpin = datetime.combine(post.date_unpin, time_).timestamp()
                        if post.date_pin < datetime.now().timestamp() < post.date_unpin:
                            if not current_post.get("is_pinned"):
                                post.pin_wall_post()
                                continue
                        if datetime.now().timestamp() > post.date_unpin:
                            if current_post.get("is_pinned"):
                                post.unpin_wall_post()


if __name__ == "__main__":
    ADSManager().control_ads_posts()
