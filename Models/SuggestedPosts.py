from peewee import *
from Models.Posts import Post, PostsHashtag


class SuggestedPost(Post):
    is_posted = BooleanField(default=False)
    is_rejected = BooleanField(default=False)
    anonymously = BooleanField(default=False)
    admin = IntegerField(null=True)
    date_of_posting = DateTimeField(formats=['%Y-%m-%d %H:%M:%S'], null=True)

    class Meta:
        table_name = 'suggested_posts'


class SuggestedPostHashtag(PostsHashtag):
    post = ForeignKeyField(SuggestedPost,
                           on_delete='CASCADE',
                           # related_name='hashtags',
                           backref='hashtags')

    class Meta:
        table_name = 'suggested_posts_hashtags'
