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
    caption_disabled = BooleanField(default=False)
    is_deleted = BooleanField(default=False)
    suggest_status = CharField(30, null=True)
    posted_by = ForeignKeyField(Admin, null=True, on_delete='SET NULL')
    posted_in = ForeignKeyField('self', null=True, on_delete='SET NULL')
    geo = CharField(null=True)

    VK_LINK = 'https://vk.ru/'

    def __str__(self):
        return '[DELETED] ' + self.get_url() if self.is_deleted else self.get_url()

    class Meta:
        table_name = 'posts'
        indexes = ['vk_id', 'owner_id', 'user']
        order_by = ['date']

    def get_url(self):
        return self.generate_url(self.id)

    @classmethod
    def generate_id(cls, owner_id, vk_id):
        return f'{owner_id}_{vk_id}'

    @classmethod
    def generate_url(cls, post_id):
        url = f'{cls.VK_LINK}wall{post_id}'
        return url


class PostsHashtag(BaseModel):
    post = ForeignKeyField(Post,
                           on_delete='CASCADE',
                           backref='hashtags')
    hashtag = TextField()

    def __str__(self):
        return self.hashtag

    class Meta:
        table_name = 'posts_hashtags'


class PostStatus(enum.Enum):
    SUGGESTED = 'SUGGESTED'
    REJECTED = 'REJECTED'
    POSTED = 'POSTED'
