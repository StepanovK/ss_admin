import random
from PIL import Image
import os
from datetime import datetime, date, timedelta
import time

import config
from utils.Scripts.vk_birthday_manager.photo_creater import PhotoCreator
import requests

from utils.connection_holder import ConnectionsHolder
from config import group_id, logger


class VKBirthdayManager:
    def __init__(self, groupId=group_id):
        dir_name = os.path.dirname(os.path.abspath(__file__))
        self._vk = ConnectionsHolder().vk_connection_admin
        self._group_id = groupId
        self.DIR_fonts = os.path.join(dir_name, 'fonts')
        self.DIR_titles = os.path.join(dir_name, 'titles')
        self._title_output = os.path.join(dir_name, 'title_out_new.png')
        self._img_back_pic = os.path.join(dir_name, 'image_back_pic2.png')
        self._title_font = os.path.join(dir_name, '17667.otf')
        self._hour_interval_posting = [9, 10]

    def getuseravatar(self, user_id):
        response = self._vk.users.get(user_ids=user_id, fields='photo_max,last_seen')
        # name = '{} {}'.format(response[0]['first_name'], response[0]['last_name'])
        if 'deactivated' not in response[0]:
            if 'last_seen' in response[0] and response[0]['last_seen']["time"] > time.time() - 31536000:
                first_name = response[0]['first_name']
                last_name = response[0]['last_name']
                photo_max = response[0]['photo_max']
                try:
                    img_data = requests.get(photo_max, stream=True)
                    im = Image.open(img_data.raw)
                except Exception:
                    im = None
            elif 'last_seen' not in response[0]:
                first_name = response[0]['first_name']
                last_name = response[0]['last_name']
                photo_max = response[0]['photo_max']
                try:
                    img_data = requests.get(photo_max, stream=True)
                    im = Image.open(img_data.raw)
                except Exception:
                    im = None
            else:
                first_name = None
                last_name = None
                im = None
        else:
            first_name = None
            last_name = None
            im = None
        return {'first_name': first_name, 'last_name': last_name, 'im': im}

    def get_group_members(self):
        members = self._vk.groups.getMembers(group_id=self._group_id, fields='bdate,sex')
        data = members["items"]
        count = members["count"] // 1000
        if members["count"] > 1000:
            for i in range(1, count + 1):
                data += self._vk.groups.getMembers(group_id=self._group_id, fields='bdate,sex', offset=i * 1000)[
                    "items"]
        members_list = []
        for elem in data:
            member = {'id': None, 'first_name': None, 'last_name': None, 'bdate': None, 'sex': None}
            try:
                if "bdate" in elem:
                    member['bdate'] = elem["bdate"]
                if 'sex' in elem:
                    member['sex'] = elem["sex"]
                member['id'] = elem["id"]
                member['first_name'] = elem["first_name"]
                member['last_name'] = elem["last_name"]
                members_list.append(member)
            except Exception:
                pass
        return members_list

    def wall_post(self, message, attachment, time_post):

        if time_post < time.time():
            time_post = time.time() + 600
        logger.info('Запуск функции отложенной  до {} публикации на стене'.format(time_post))
        upload_url = self._vk.photos.getWallUploadServer(group_id=self._group_id)['upload_url']
        request = requests.post(upload_url, files={'photo': open(attachment, "rb")})
        params = {'server': request.json()['server'],
                  'photo': request.json()['photo'],
                  'hash': request.json()['hash'],
                  'group_id': self._group_id}

        # Сохраняем картинку на сервере и получаем её идентификатор
        photo_id = self._vk.photos.saveWallPhoto(**params)[0]
        photo_attach = 'photo' + str(photo_id['owner_id']) + '_' + str(photo_id['id'])

        # Формируем параметры для размещения картинки в группе и публикуем её
        params = {'attachments': photo_attach,
                  'message': message,
                  'owner_id': f"-{self._group_id}",
                  'from_group': '1',
                  'publish_date': int(time_post)
                  }
        self._vk.wall.post(**params)

    @staticmethod
    def get_hbday_users(dict_users, d_now):
        users = []
        for user in dict_users:
            if user['bdate'] is not None:
                bdate = user['bdate'].split('.')
                bdate = bdate[0] + '.' + bdate[1]
                if bdate == d_now:
                    users.append(
                        {'id': user['id'], 'first_name': user['first_name'], 'last_name': user['last_name'],
                         'bdate': user['bdate']})
        return users

    def send_happy_birthday(self):
        name_group = self._vk.groups.getById(group_ids=self._group_id, fields='description')[0]['name']
        photo_group = self._vk.groups.getById(group_ids=self._group_id, fields='description')[0]['photo_200']
        photo_group = requests.get(photo_group, stream=True)
        photo_group = Image.open(photo_group.raw)
        Today = datetime.now()
        y = Today.year
        m = Today.month
        d = Today.day
        m_list = [i for i in range(60)]
        time_post = datetime(y, m, d, random.choice(self._hour_interval_posting), random.choice(m_list)).timestamp()
        group_members = self.get_group_members()
        d_now = '{dt.day}.{dt.month}'.format(dt=datetime.now())

        hbday_users = self.get_hbday_users(group_members, d_now)
        if len(hbday_users) == 0:
            return

        memcounter = PhotoCreator(os.path.join(self.DIR_titles, random.choice(os.listdir(self.DIR_titles))), 200,
                                  os.path.join(self.DIR_fonts, random.choice(os.listdir(self.DIR_fonts))), 48)
        message = 'Поздравляем с днем рождения подписчиков нашей группы!!!' \
                  '\nСегодня, {}, свой день рождения празднуют: '.format(
            datetime.today().strftime('%d.%m.%Y'))
        for user in hbday_users:
            user_info = self.getuseravatar(user['id'])
            if user_info['last_name'] is not None:
                message += '[id{}|{} {}], '.format(user['id'], user_info['first_name'], user_info['last_name'])
                memcounter.add_users(user_info['im'], user_info['first_name'], user_info['last_name'])
        memcounter.create_cover(self._img_back_pic,
                                '{} поздравляет своих подписчиков с днем рождения!'.format(name_group), 144,
                                self._title_font, photo_group)
        message = message[:-2]
        self.wall_post(message, self._title_output, time_post)


def send_happy_birthday():
    logger.info('send happy birthday started')
    if config.debug:
        logger.info('debug: send happy birthday skipped')
    else:
        VKBirthdayManager().send_happy_birthday()
    logger.info('send happy birthday finished')


if __name__ == "__main__":
    VKBirthdayManager().send_happy_birthday()
