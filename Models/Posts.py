from peewee import *
from base import BaseModel
from Users import User


# https://peewee.readthedocs.io/en/latest/peewee/example.html
# https://www.youtube.com/watch?v=YyOvitek6H8


class Post(BaseModel):
    id = IntegerField(unique=True, primary_key=True)
    user_id = ForeignKeyField(User, on_delete='CASCADE', index=True)
    signed_id = IntegerField(index=True)
    date = DateField(formats=['%Y-%m-%d %H:%M:%S'])
    text = TextField()
    is_deleted = BooleanField()

    class Meta:
        table_name = 'posts'
        primary_key = 'id'

    def pars_wall_post(self, wall_post):
        pass
        # if wall_post.type == VkBotEventType.WALL_POST_NEW:
        #     self.text = wall_post.object['text']
        #     self.user_id = wall_post.object['from_id']
        #     self.user_info = get_user_info(self.user_id)
        #     self.date = wall_post.object['date']
        #     self.post_type = wall_post.object['post_type']
        #     self.post_id = wall_post.object['id']
        #     self.owner_id = wall_post.object['owner_id']
        #     if self.owner_id is not None and self.post_id is not None:
        #         self.link = f'{vk_link}wall{self.owner_id}_{self.post_id}'
        #     for attachment in wall_post.object.get('attachments', []):
        #         attachment_type = attachment.get('type')
        #         if attachment_type == 'photo':
        #             sizes = attachment.get('photo', {}).get('sizes', [])
        #             if len(sizes) > 0:
        #                 max_size = sizes[-1]
        #                 try:
        #                     photo = download(max_size['url'], out=cache_dir)
        #                     photo = photo.replace('/', '\\')
        #                 except Exception as _ex:
        #                     photo = None
        #                     logger.error(f'Ошибка при загрузки фото: \n{attachment} \n{_ex}')
        #                 if photo:
        #                     self.photo.append(photo)
        #                     # with open(photo, 'rb') as photo_file:
        #                     #     self.photo.append(photo_file)
        #                     # os.remove(photo)
        #
        # # @logger.catch()
