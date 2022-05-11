import datetime

from peewee import *
from Models.base import BaseModel
from Models.Users import User


# https://peewee.readthedocs.io/en/latest/peewee/example.html
# https://www.youtube.com/watch?v=YyOvitek6H8


class Post(BaseModel):
    id = PrimaryKeyField()
    user = ForeignKeyField(User, on_delete='CASCADE', index=True, backref='posts')
    signed_id = CharField(null=True)
    owner_id = CharField()
    date = DateField(formats=['%Y-%m-%d %H:%M:%S'])
    text = TextField(default='')
    is_deleted = BooleanField(default=False)

    vk_link = 'https://vk.com/'

    class Meta:
        table_name = 'posts'

    def gev_url(self):
        url = f'{self.vk_link}wall{self.owner_id}_{self.id}'
        return url

    def pars_wall_post(self, wall_post, vk_connection):
        self.id = wall_post['id']
        self.text = wall_post['text']
        self.user = User.get_or_create_user(wall_post['from_id'], vk_connection)
        self.date = datetime.datetime.fromtimestamp(wall_post['date'])
        self.owner_id = str(wall_post['owner_id'])

        self.save(force_insert=True)

        for attachment in wall_post.get('attachments', []):
            attachment_type = attachment.get('type')
            if attachment_type == 'photo':
                sizes = attachment.get('photo', {}).get('sizes', [])
                if len(sizes) > 0:
                    max_size = sizes[-1]
                    # try:
                    #     photo = download(max_size['url'], out=cache_dir)
                    #     photo = photo.replace('/', '\\')
                    # except Exception as _ex:
                    #     photo = None
                    #     # logger.error(f'Ошибка при загрузки фото: \n{attachment} \n{_ex}')
                    # if photo:
                    #     self.photo.append(photo)
                    #     # with open(photo, 'rb') as photo_file:
                    #     #     self.photo.append(photo_file)
                    #     # os.remove(photo)


class PostsHashtag(BaseModel):
    post = ForeignKeyField(Post,
                           on_delete='CASCADE',
                           related_name='hashtags',
                           backref='hashtags')
    hashtag = TextField()

    class Meta:
        table_name = 'posts_hashtags'


