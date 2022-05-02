from peewee import *
from base import BaseModel
from Attachments import Attachment
from Posts import Post
from Users import User


class PostsAttachment(BaseModel):
    post_id = ForeignKeyField(Post, index=True)
    attachment_id = ForeignKeyField(Attachment, index=True)
    is_deleted = BooleanField()

    class Meta:
        table_name = 'posts_attachments'

