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
    replied_comment = ForeignKeyField('self', null=True)
    replied_to_user = IntegerField(null=True)
    date = DateTimeField(formats=['%Y-%m-%d %H:%M:%S'])
    text = TextField()
    is_deleted = BooleanField()

    class Meta:
        table_name = 'comments'
        indexes = ['user', 'post']
        order_by = ['post', 'date']

