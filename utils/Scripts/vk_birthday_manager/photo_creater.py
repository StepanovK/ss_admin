import os

from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw


def prepare_mask(size, antialias=2):
    mask = Image.new('L', (size[0] * antialias, size[1] * antialias), 0)
    ImageDraw.Draw(mask).ellipse((0, 0) + mask.size, fill=255)
    return mask.resize(size, Image.ANTIALIAS)


def crop(im, s):
    w, h = im.size
    k = w / s[0] - h / s[1]
    if k > 0:
        im = im.crop(((w - h) / 2, 0, (w + h) / 2, h))
    elif k < 0:
        im = im.crop((0, (h - w) / 2, w, (h + w) / 2))
    return im.resize(s, Image.ANTIALIAS)


class PhotoCreator:
    def __init__(self, cover, default_size_avatar, text_font, default_size_text):
        self.flag = False
        self.count_photos = 0
        self.count_last_column = 0
        self.cover = cover
        self.coefficient = 1
        self.coefficients = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]
        self.default_size_avatar = default_size_avatar
        self.size_user_pic_back = None
        self.text_font = text_font
        self.text_font_title = None
        self.default_size_text = default_size_text
        self.count_rows = 1
        self.count_columns = 1
        self.list_users = []
        self.title = None
        self.title_w = None
        self.title_h = None
        self.user_pic_back = None
        self.last_title_text = None
        self._dirname = os.path.dirname(os.path.abspath(__file__))
        self._photo_group = os.path.join(self._dirname, 'photo_group.png')
        self._image_output_krug = os.path.join(self._dirname, 'image_output_krug.png')
        self._camera_404 = os.path.join(self._dirname, 'camera_200.jpg')
        self._last_title_text = os.path.join(self._dirname, 'last_title_text.png')
        self._title_output = os.path.join(self._dirname, 'title_out_new.png')

    def add_users(self, user_pic, user_first_name, user_last_name):
        self.list_users.append({'user_pic': user_pic,
                                'user_first_name': user_first_name,
                                'user_last_name': user_last_name})
        self.count_photos += 1

    def resize_users_pic(self, frame_width=100, frame_height=100):
        self.title = Image.open(self.cover)
        self.title_w, self.title_h = self.title.size
        if self.count_photos > 0:
            for self.coefficient in self.coefficients:
                new_size_ava = int(self.default_size_avatar * self.coefficient)
                count_photos_in_row = self.count_photos
                if new_size_ava * count_photos_in_row + 150 * (
                        count_photos_in_row - 1) * self.coefficient > self.title_w - frame_width:
                    while new_size_ava * count_photos_in_row + 150 * (
                            count_photos_in_row - 1) * self.coefficient > self.title_w - frame_width:
                        count_photos_in_row -= 1
                self.count_columns = count_photos_in_row
                self.count_rows = self.count_photos // self.count_columns
                if self.count_photos > (self.count_rows * self.count_columns):
                    self.count_last_column = self.count_photos - (self.count_rows * self.count_columns)
                    self.count_rows += 1
                    self.flag = True
                else:
                    self.flag = False
                ava_count_h = int(new_size_ava * self.count_rows + 200 * self.count_rows * self.coefficient)
                if ava_count_h <= self.title_h - frame_height:
                    self.default_size_avatar = new_size_ava
                    break

    def create_cover(self, back_pic=None, title_text=None, title_text_size=None, text_font_title=None,
                     photo_group=None):
        self.resize_users_pic(frame_width=100, frame_height=200)
        if back_pic is not None:
            self.size_user_pic_back = self.default_size_avatar + int(100 * self.coefficient)
            self.user_pic_back = Image.open(back_pic)
            self.user_pic_back = crop(self.user_pic_back,
                                      (self.size_user_pic_back, self.size_user_pic_back))

        if title_text is not None:
            self.text_font_title = text_font_title
            draw = ImageDraw.Draw(self.title)
            font = ImageFont.truetype(self.text_font_title, title_text_size)
            w_title_text, h_title_text = font.getsize(title_text)
            if w_title_text > self.title_w:
                while w_title_text > self.title_w:
                    title_text_size -= 1
                    font = ImageFont.truetype(self.text_font_title, title_text_size)
                    w_title_text, h_title_text = font.getsize(title_text)
            self.last_title_text = Image.open(self._last_title_text).convert("RGBA")
            self.last_title_text = crop(self.last_title_text,
                                        (self.title_w, h_title_text + 20))
            self.title.paste(self.last_title_text, (0, 0),
                             self.last_title_text)
            draw.text(((self.title_w // 2) - w_title_text // 2,
                       20),
                      title_text,
                      (0, 0, 0),
                      font=font)
        if photo_group is not None:
            photo_group = crop(photo_group, (self.default_size_avatar, self.default_size_avatar))
            photo_group.putalpha(
                prepare_mask((self.default_size_avatar, self.default_size_avatar), 4))
            photo_group.save(self._photo_group)
            photo_group = Image.open(self._photo_group).convert("RGBA")
            self.title.paste(photo_group, (self.title_w - self.default_size_avatar,
                                           self.title_h - self.default_size_avatar),
                             photo_group)
        i = 0
        # for user in self.list_users:
        for x in range(int(self.count_rows)):
            for y in range(int(self.count_columns)):
                if i < self.count_photos:
                    print(self.list_users[i]['user_last_name'])
                    try:
                        self.list_users[i]['user_pic'] = crop(self.list_users[i]['user_pic'],
                                                              (self.default_size_avatar, self.default_size_avatar))
                        self.list_users[i]['user_pic'].putalpha(
                            prepare_mask((self.default_size_avatar, self.default_size_avatar), 4))
                        self.list_users[i]['user_pic'].save(self._image_output_krug)
                        self.list_users[i]['user_pic'] = Image.open(self._image_output_krug).convert("RGBA")
                    except Exception:
                        self.list_users[i]['user_pic'] = crop(Image.open(self._camera_404),
                                                              (self.default_size_avatar, self.default_size_avatar))
                        self.list_users[i]['user_pic'].putalpha(
                            prepare_mask((self.default_size_avatar, self.default_size_avatar), 4))
                        self.list_users[i]['user_pic'].save(self._image_output_krug)
                        self.list_users[i]['user_pic'] = Image.open(self._image_output_krug).convert("RGBA")
                    # ava_w, ava_h = ava.size
                    ava_coord_w = self.title_w // 2 - (
                            self.default_size_avatar * self.count_columns + 150 * (
                            self.count_columns - 1) * self.coefficient) // 2 + (
                                          self.default_size_avatar + 150 * self.coefficient) * y
                    ava_coord_h = self.title_h // 2 - (self.default_size_avatar * self.count_rows + 200 * (
                            self.count_rows - 1) * self.coefficient) // 2 + (
                                          self.default_size_avatar + 200 * self.coefficient) * x
                    if x == self.count_rows - 1 and self.flag:
                        ava_coord_w = self.title_w // 2 - (
                                self.default_size_avatar * self.count_last_column + 150 * (
                                self.count_last_column - 1) * self.coefficient) // 2 + (
                                              self.default_size_avatar + 150 * self.coefficient) * y
                    if self.user_pic_back is not None:
                        self.title.paste(self.user_pic_back, (
                            int(ava_coord_w) - int((self.size_user_pic_back - self.default_size_avatar) // 2),
                            int(ava_coord_h) - int((self.size_user_pic_back - self.default_size_avatar) // 2)),
                                         self.user_pic_back)
                    self.title.paste(self.list_users[i]['user_pic'], (int(ava_coord_w), int(ava_coord_h)),
                                     self.list_users[i]['user_pic'])
                    draw = ImageDraw.Draw(self.title)
                    font = ImageFont.truetype(self.text_font, int(self.default_size_text * self.coefficient))
                    w_first_name, h_first_name = font.getsize(self.list_users[i]['user_first_name'])
                    self.last_title_text = Image.open(self._last_title_text).convert("RGBA")
                    self.last_title_text = crop(self.last_title_text,
                                                (int(w_first_name), int(h_first_name)))

                    self.title.paste(self.last_title_text,
                                     (int((ava_coord_w + self.default_size_avatar // 2) - w_first_name // 2),
                                      int(ava_coord_h + self.default_size_avatar + int(40 * self.coefficient))),
                                     self.last_title_text)
                    w_last_name, h_last_name = font.getsize(self.list_users[i]['user_last_name'])

                    if w_last_name > self.default_size_avatar + 150 * self.coefficient:
                        while w_last_name > self.default_size_avatar + 150 * self.coefficient:
                            self.list_users[i]['user_last_name'] = self.list_users[i]['user_last_name'][:-1]
                            w_last_name, h_last_name = font.getsize(self.list_users[i]['user_last_name'])
                        else:
                            self.list_users[i]['user_last_name'] = self.list_users[i]['user_last_name'][:-1] + '...'
                            w_last_name, h_last_name = font.getsize(self.list_users[i]['user_last_name'])

                    self.last_title_text = Image.open(self._last_title_text).convert("RGBA")
                    self.last_title_text = crop(self.last_title_text,
                                                (w_last_name, h_last_name))
                    self.title.paste(self.last_title_text,
                                     (int((ava_coord_w + self.default_size_avatar // 2) - w_last_name / 2),
                                      int(ava_coord_h + self.default_size_avatar + 40 * self.coefficient + int(
                                          self.default_size_text * self.coefficient))),
                                     self.last_title_text)
                    draw.text(((ava_coord_w + self.default_size_avatar // 2) - w_first_name // 2,
                               ava_coord_h + self.default_size_avatar + int(40 * self.coefficient)),
                              self.list_users[i]['user_first_name'],
                              (0, 0, 0),
                              font=font)

                    draw.text(
                        ((ava_coord_w + self.default_size_avatar // 2) - w_last_name / 2,
                         ava_coord_h + self.default_size_avatar + 40 * self.coefficient + int(
                             self.default_size_text * self.coefficient)),
                        self.list_users[i]['user_last_name'],
                        (0, 0, 0), font=font)
                    i += 1

        self.title.save(self._title_output)
