from peewee import *
from base import BaseModel
from Attachments import Attachment
from Posts import Post
from SuggestedPosts import SuggestedPost
from Comments import Comment


class CommentsAttachment(BaseModel):
    comment = ForeignKeyField(Comment,
                              index=True,
                              related_name='attachments',
                              backref='attachments',
                              on_delete='CASCADE')
    attachment = ForeignKeyField(Attachment, index=True)
    is_deleted = BooleanField()

    class Meta:
        table_name = 'comments_attachments'
        indexes = ['comment']
        order_by = ['comment']


class CommentsLike(BaseModel):
    comment = ForeignKeyField(Comment,
                              on_delete='CASCADE',
                              related_name='likes',
                              backref='likes')
    user = ForeignKeyField(Post,
                           on_delete='CASCADE',
                           related_name='liked_comments',
                           backref='liked_comments')

    class Meta:
        table_name = 'comments_likes'


class PostsAttachment(BaseModel):
    post = ForeignKeyField(Post,
                           index=True,
                           related_name='attachments',
                           backref='attachments',
                           on_delete='CASCADE')
    attachment = ForeignKeyField(Attachment, index=True)
    is_deleted = BooleanField()

    class Meta:
        table_name = 'posts_attachments'
        indexes = ['post']
        order_by = ['post']


class PostsLike(BaseModel):
    post = ForeignKeyField(Post,
                           on_delete='CASCADE',
                           related_name='likes',
                           backref='likes')
    user = ForeignKeyField(Post,
                           on_delete='CASCADE',
                           related_name='liked_posts',
                           backref='liked_posts')

    class Meta:
        table_name = 'posts_likes'


class SuggestedPostsAttachment(BaseModel):
    post = ForeignKeyField(SuggestedPost,
                           index=True,
                           related_name='attachments',
                           backref='attachments',
                           on_delete='CASCADE')
    attachment = ForeignKeyField(Attachment, index=True)
    is_deleted = BooleanField()

    class Meta:
        table_name = 'suggested_posts_attachments'
        indexes = ['post']
        order_by = ['post']
