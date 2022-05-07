from peewee import *
from base import BaseModel
from Users import User
from Posts import Post, PostHashtag


# https://peewee.readthedocs.io/en/latest/peewee/example.html
# https://www.youtube.com/watch?v=YyOvitek6H8


class SuggestedPost(Post):
    is_posted = BooleanField()
    is_rejected = BooleanField()
    anonymously = BooleanField()
    admin = IntegerField()
    date_of_posting = DateField(formats=['%Y-%m-%d %H:%M:%S'])

    class Meta:
        table_name = 'suggested_posts'


class SuggestedPostHashtag(PostHashtag):

    class Meta:
        table_name = 'suggested_posts_hashtags'


