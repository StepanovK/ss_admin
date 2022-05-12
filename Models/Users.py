from peewee import *
from Models.base import BaseModel
from config import logger
import datetime


class User(BaseModel):
    id = PrimaryKeyField()
    first_name = CharField(100, default='', null=True)
    last_name = CharField(100, default='', null=True)
    city = CharField(100, default='', null=True)
    sex = CharField(10, null=True)
    birth_date = DateField(null=True)
    domain = CharField(100, default='')
    is_active = BooleanField(default=True)

    class Meta:
        table_name = 'users'

    @classmethod
    def get_or_create_user(cls, vk_id: int, vk_connection=None):
        try:
            user = cls.get_by_id(vk_id)
        except User.DoesNotExist:
            user = User.create(id=vk_id)
            if vk_connection is not None:
                user.update_info_from_vk(vk_id, vk_connection)
                user.save()

        return user

    @staticmethod
    def vk_get_user_info(user_id: int, vk_connection):
        user_info = {
            'id': user_id,
            'first_name': '',
            'last_name': '',
            'photo_max': '',
            'last_seen': '',
            'birth_date': None,
            'city': '',
            'can_write_private_message': False,
            'sex': '',
            'user_info_was_found': False
        }
        fields = 'id, first_name,last_name, photo_max, last_seen, domain, ' \
                 'city, can_write_private_message, online, sex, bdate, ' \
                 'photo_max_orig, photo_50'
        try:
            response = vk_connection.users.get(user_ids=user_id, fields=fields)
            if isinstance(response, list) and len(response) > 0:
                user_info.update(response[0])
                city = user_info['city']
                user_info['city'] = city.get('title', '') if isinstance(city, dict) else str(city)
                sex = user_info.get('sex', 0)
                user_info['sex'] = 'female' if sex == 1 else 'male' if sex == 2 else ''
                user_info['can_write_private_message'] = bool(user_info.get('can_write_private_message', 0))
                user_info['user_info_was_found'] = True
                if 'bdate' in user_info:
                    time_parts = str(user_info.get('bdate', '')).split('.')
                    if len(time_parts) == 3:
                        user_info['birth_date'] = datetime.date(int(time_parts[2]), int(time_parts[1]),
                                                                int(time_parts[0]))
                    elif len(time_parts) == 2:
                        user_info['birth_date'] = datetime.date(1900, int(time_parts[1]), int(time_parts[0]))

        except Exception as ex:
            logger.error(f"Ошибка получения информации о пользователе id{user_id}: {ex}")
        return user_info

    def update_info_from_vk(self, vk_id: int, vk_connection):
        user_info = self.vk_get_user_info(vk_id, vk_connection)
        if user_info.get('user_info_was_found', False):
            self.first_name = user_info.get('first_name')
            self.last_name = user_info.get('last_name')
            self.city = user_info.get('city', '')
            self.birth_date = user_info.get('birth_date')
            self.sex = user_info.get('sex', '')
            self.is_active = user_info.get('deactivated') is None
            self.domain = user_info.get('domain', '')

    def chat_name(self):
        f_name = self.full_name()
        if f_name == '':
            return f'[id{self.id}]'
        else:
            return f'[id{self.id}|{f_name}]'

    def full_name(self):
        f_name = f'{self.last_name} {self.first_name}'
        return f_name.strip()
