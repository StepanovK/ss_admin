from peewee import *
from Models.Posts import Post, PostsHashtag


# https://peewee.readthedocs.io/en/latest/peewee/example.html
# https://www.youtube.com/watch?v=YyOvitek6H8


class SuggestedPost(Post):
    is_posted = BooleanField(default=False)
    is_rejected = BooleanField(default=False)
    anonymously = BooleanField(default=False)
    admin = IntegerField(null=True)
    date_of_posting = DateField(formats=['%Y-%m-%d %H:%M:%S'], null=True)

    class Meta:
        table_name = 'suggested_posts'


class SuggestedPostHashtag(PostsHashtag):

    class Meta:
        table_name = 'suggested_posts_hashtags'


