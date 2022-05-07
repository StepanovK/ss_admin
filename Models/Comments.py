from peewee import *
from base import BaseModel
from Users import User
from Posts import Post


class Comment(BaseModel):
    id = IntegerField(primary_key=True)
    user = ForeignKeyField(User,
                           backref='comments',
                           related_name='comments', )
    group = IntegerField(null=True)
    post = ForeignKeyField(Post,
                           backref='comments',
                           related_name='comments',
                           on_delete='CASCADE')
    replied_comment = IntegerField(null=True)
    replied_to_user = IntegerField(null=True)
    date = DateTimeField()
    text = TextField()
    is_deleted = BooleanField()

    class Meta:
        table_name = 'comments'
        primary_key = 'id'
        indexes = ['user', 'post']
        order_by = ['post', 'date']


class CommentLikes(BaseModel):
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