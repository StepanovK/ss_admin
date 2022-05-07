from peewee import *
from base import BaseModel
from Attachments import Attachment
from Posts import Post
from Comments import Comment


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
