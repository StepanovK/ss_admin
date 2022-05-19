from peewee import *
from Models.base import BaseModel
from Models.Users import User
from Models.Admins import Admin
import enum


class Post(BaseModel):
    id = CharField(100, primary_key=True)
    vk_id = IntegerField(null=True)
    user = ForeignKeyField(User, on_delete='CASCADE', index=True, backref='posts', null=True)
    owner_id = IntegerField(null=True)
    date = DateTimeField(formats=['%Y-%m-%d %H:%M:%S'], null=True)
    text = TextField(default='')
    marked_as_ads = BooleanField(default=False)
    anonymously = BooleanField(default=False)
    is_deleted = BooleanField(default=False)
    suggest_status = CharField(30, null=True)
    posted_by = ForeignKeyField(Admin, null=True, on_delete='SET NULL')
    posted_in = ForeignKeyField('self', null=True, on_delete='SET NULL')

    VK_LINK = 'https://vk.com/'

    def __str__(self):
        return self.get_url()

    class Meta:
        table_name = 'posts'
        indexes = ['vk_id', 'owner_id', 'user']
        order_by = ['date']

    def get_url(self):
        url = f'{self.VK_LINK}wall{self.id}'
        return url

    @classmethod
    def generate_id(cls, owner_id, vk_id):
        return f'{owner_id}_{vk_id}'


class PostsHashtag(BaseModel):
    post = ForeignKeyField(Post,
                           on_delete='CASCADE',
                           backref='hashtags')
    hashtag = TextField()

    class Meta:
        table_name = 'posts_hashtags'


class PostStatus(enum.Enum):
    SUGGESTED = 'SUGGESTED'
    REJECTED = 'REJECTED'
    POSTED = 'POSTED'
