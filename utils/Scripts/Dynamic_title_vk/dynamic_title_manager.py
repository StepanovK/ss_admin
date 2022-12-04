from datetime import datetime
import time

from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

import requests
import os

from utils.connection_holder import ConnectionsHolder
from config import group_id, token_weather, logger


class DynamicTitleManager:
    def __init__(self, groupId: str = group_id, tokenWeather: str = token_weather):
        dir_name = os.path.dirname(os.path.abspath(__file__))
        self._vk = ConnectionsHolder().vk_connection_admin
        self._group_id = groupId
        self._token_weather = tokenWeather
        self._weather: dict = None
        self._img_ava_d: str = os.path.join(dir_name, 'ava_d.png')
        self._img_ava_n: str = os.path.join(dir_name, 'ava_n.png')
        self._img_ava: str = os.path.join(dir_name, 'ava.png')
        self._img_title_d: str = os.path.join(dir_name, 'title.jpg')
        self._img_title_n: str = os.path.join(dir_name, 'title.jpg')
        self._img_title: str = os.path.join(dir_name, 'title.png')
        self._img_default_weather_icon: str = os.path.join(dir_name, 'icon_weather_0.png')
        self._img_weather_icon: str = os.path.join(dir_name, 'icon_weather.png')
        self._img_title_output: str = os.path.join(dir_name, 'title_img-out.png')
        self._img_back_avatar: str = os.path.join(dir_name, 'image_back_white.png')
        self._font: str = os.path.join(dir_name, 'Roboto-Bold.ttf')
        self._font_size: int = 16

    def _get_weather(self, lat: str = '56.328674', lon: str = '44.002048') -> str:
        logger.info("Start get weather")

        data = {'lat': lat, 'lon': lon,
                'units': 'metric', 'lang': 'ru',
                'exclude': 'current,minutely,hourly', 'APPID': self._token_weather}
        url = f"https://api.openweathermap.org/data/2.5/weather"
        response = requests.post(url, params=data)
        if response.status_code == 200:
            self._weather = response.json()
            return response.json()

    def _get_text_title(self) -> str:
        if self._get_weather():
            if 'd' in self._weather['weather'][0]['icon']:
                image = Image.open(self._img_ava_d)
                image.save(self._img_ava)
                image = Image.open(self._img_title_d)
                image.save(self._img_title)
            else:
                image = Image.open(self._img_ava_n)
                image.save(self._img_ava)
                image = Image.open(self._img_title_d)
                image.save(self._img_title)
            if self._weather['weather'][0]['icon'] == '02d' or self._weather['weather'][0]['icon'] == '02n':
                self._weather['weather'][0]['icon'] = '03d'
            elif self._weather['weather'][0]['icon'] == '10d' or self._weather['weather'][0]['icon'] == '10n':
                self._weather['weather'][0]['icon'] = '09d'
            if self._weather['weather'][0]['icon'] != '01d' and self._weather['weather'][0]['icon'] != '01n':
                weather_icon = 'http://openweathermap.org/img/wn/{}@2x.png'.format(self._weather['weather'][0]['icon'])
                img_data = requests.get(weather_icon, stream=True)
                image = Image.open(img_data.raw)
                image.save(self._img_weather_icon)
            else:
                image = Image.open(self._img_default_weather_icon)
                image.save(self._img_weather_icon)
            result = '{}\nСейчас {}\nТемпература {} {}C\nВетер {} м/с'.format(datetime.date(datetime.now()),
                                                                              self._weather['weather'][0][
                                                                                  'description'],
                                                                              int(self._weather['main']["temp"]),
                                                                              u"\u00b0",
                                                                              self._weather["wind"]['speed'])
        else:
            image = Image.open(self._img_ava_d)
            image.save(self._img_ava)
            image = Image.open(self._img_title_d)
            image.save(self._img_title)
            image = Image.open(self._img_default_weather_icon)
            image.save(self._img_weather_icon)
            result = '{}\nСейчас\nТемпература \nВетер м/с'.format(datetime.date(datetime.now()))
        return result

    def wall_post(self, message, attachment, OWNER_ID, time_post):
        if OWNER_ID[0] == '-':
            OWNER_ID = OWNER_ID[1:]
        if time_post < time.time():
            time_post = time.time() + 600
        logger.info('Запуск функции отложенной  до {} публикации на стене'.format(time_post))
        upload_url = self._vk.photos.getWallUploadServer(group_id=OWNER_ID)['upload_url']
        request = requests.post(upload_url, files={'photo': open(attachment, "rb")})
        params = {'server': request.json()['server'],
                  'photo': request.json()['photo'],
                  'hash': request.json()['hash'],
                  'group_id': OWNER_ID}

        # Сохраняем картинку на сервере и получаем её идентификатор
        photo_id = self._vk.photos.saveWallPhoto(**params)[0]
        photo_attach = 'photo' + str(photo_id['owner_id']) + '_' + str(photo_id['id'])

        # Формируем параметры для размещения картинки в группе и публикуем её
        params = {'attachments': photo_attach,
                  'message': message,
                  'owner_id': '-' + OWNER_ID,
                  'from_group': '1',
                  'publish_date': int(time_post)
                  }
        self._vk.wall.post(**params)

    def getlostuser(self, group_id):
        logger.info('Запуск функции получения данных о последнем вступившем в группу пользователе')
        count_users = self._vk.groups.getMembers(group_id=int(group_id),
                                                 sort='time_desc')['count']
        lostuser = self._vk.groups.getMembers(group_id=int(group_id),
                                              sort='time_desc')['items'][0]
        return lostuser

    def getuseravatar(self, user_id):
        logger.info('Запуск функции получения аватара и имени пользователя')
        response = self._vk.users.get(user_ids=user_id, fields='photo_max,last_seen')
        if 'deactivated' not in response[0]:
            if 'last_seen' in response[0] and response[0]['last_seen']["time"] > time.time() - 31536000:
                first_name = response[0]['first_name']
                last_name = response[0]['last_name']
                photo_max = response[0]['photo_max']
                img_data = requests.get(photo_max, stream=True)
                im = Image.open(img_data.raw)
            else:
                first_name = None
                last_name = None
                im = None
        else:
            first_name = None
            last_name = None
            im = None
        return {'first_name': first_name, 'last_name': last_name, 'im': im}

    @staticmethod
    def prepare_mask(size, antialias=2):
        mask = Image.new('L', (size[0] * antialias, size[1] * antialias), 0)
        ImageDraw.Draw(mask).ellipse((0, 0) + mask.size, fill=255)
        return mask.resize(size, Image.ANTIALIAS)

    @staticmethod
    def crop(im, s):
        w, h = im.size
        k = w / s[0] - h / s[1]
        if k > 0:
            im = im.crop(((w - h) / 2, 0, (w + h) / 2, h))
        elif k < 0:
            im = im.crop((0, (h - w) / 2, w, (h + w) / 2))
        return im.resize(s, Image.ANTIALIAS)

    def upload_title(self):
        self.create_title()
        logger.info('Запуск функции загрузки обложки на сервер VK')
        upload_url = \
            self._vk.photos.getOwnerCoverPhotoUploadServer(group_id=self._group_id, crop_x=0, crop_y=0, crop_x2=911,
                                                           crop_y2=364)[
                'upload_url']
        request = requests.post(upload_url, files={'photo': open(self._img_title_output, "rb")})
        params = {'hash': request.json()['hash'],
                  'photo': request.json()['photo']}
        self._vk.photos.saveOwnerCoverPhoto(**params)

    def create_title(self):
        weather = self._get_text_title()
        title = Image.open(self._img_title)
        title_w, title_h = title.size
        draw = ImageDraw.Draw(title)
        font = ImageFont.truetype(self._font, self._font_size)
        w_weather, h_weather = font.getsize(weather)
        weather_im = Image.open(self._img_weather_icon)
        draw.text((100, 60), weather, (100, 100, 100),
                  font=font)
        ava = Image.open(self._img_ava).convert("RGBA")
        ava = DynamicTitleManager().crop(ava, (75, 75))
        ava_w, ava_h = ava.size
        title.paste(ava, (0, 50),
                    ava)
        title.paste(weather_im, (0, 60), weather_im)
        back_pic = Image.open(self._img_back_avatar).convert("RGBA")
        back_pic = DynamicTitleManager().crop(back_pic, (85, 85))
        back_pic.putalpha(DynamicTitleManager().prepare_mask((85, 85), 4))
        title.paste(back_pic, (title_w - 100 - 85, 90),
                    back_pic)
        last_user = self.getuseravatar(self.getlostuser(self._group_id))
        last_user_ava = last_user['im'].convert("RGBA")
        last_user_ava = DynamicTitleManager().crop(last_user_ava, (75, 75))
        last_user_ava.putalpha(DynamicTitleManager().prepare_mask((75, 75), 4))
        title.paste(last_user_ava, (title_w - 100 - 80, 95),
                    last_user_ava)
        font = ImageFont.truetype(self._font, self._font_size)
        last_user_first_name = last_user['first_name']
        last_user_last_name = last_user['last_name']
        w_first_name, h_first_name = font.getsize(last_user_first_name)
        w_last_name, h_last_name = font.getsize(last_user_last_name)
        draw.text((title_w - 142 - w_first_name // 2, 180), last_user_first_name, (255, 255, 255),
                  font=font)
        draw.text((title_w - 142 - w_last_name // 2, 195), last_user_last_name, (255, 255, 255),
                  font=font)
        new_user = 'Новый подписчик'
        w_new_user, h_new_user = font.getsize(new_user)
        draw.text((title_w - 142 - w_new_user // 2, 60), new_user, (255, 255, 255),
                  font=font)

        title.save(self._img_title_output)


def update_title_vk():
    logger.info('Dynamic title post started')
    DynamicTitleManager().upload_title()
    logger.info('Dynamic title post finished')

# if __name__ == "__main__":
#     print(DynamicTitleManager().upload_title_img())
