from peewee import *
from Models.base import BaseModel
from Models.Users import User


# https://peewee.readthedocs.io/en/latest/peewee/example.html
# https://www.youtube.com/watch?v=YyOvitek6H8


class Post(BaseModel):
    id = PrimaryKeyField()
    user = ForeignKeyField(User, on_delete='CASCADE', index=True, backref='posts')
    signed_id = CharField(30, null=True)
    owner_id = CharField(30)
    date = DateTimeField(formats=['%Y-%m-%d %H:%M:%S'])
    text = TextField(default='')
    is_deleted = BooleanField(default=False)

    vk_link = 'https://vk.com/'

    def __str__(self):
        return self.get_url()

    class Meta:
        table_name = 'posts'

    def get_url(self):
        url = f'{self.vk_link}wall{self.owner_id}_{self.id}'
        return url


class PostsHashtag(BaseModel):
    post = ForeignKeyField(Post,
                           on_delete='CASCADE',
                           related_name='hashtags',
                           backref='hashtags')
    hashtag = TextField()

    class Meta:
        table_name = 'posts_hashtags'
