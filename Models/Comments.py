from peewee import *
from Models.base import BaseModel
from Models.Users import User
from Models.Posts import Post


class Comment(BaseModel):
    id = PrimaryKeyField()
    vk_id = IntegerField()
    owner_id = IntegerField()
    user = ForeignKeyField(User, backref='comments', null=True)
    post = ForeignKeyField(Post, backref='comments', on_delete='CASCADE', null=True)
    replied_comment = ForeignKeyField('self', null=True)
    replied_to_user = ForeignKeyField(User, null=True)
    date = DateTimeField(formats=['%Y-%m-%d %H:%M:%S'], null=True)
    text = TextField(default='')
    is_deleted = BooleanField(default=False)

    class Meta:
        table_name = 'comments'
        indexes = ['user', 'post', 'vk_id']
        order_by = ['post', 'date']

    def get_url(self):
        str_thread = '' if self.replied_comment is None else f'&thread={self.replied_comment.vk_id}'
        url = f'{self.post}?reply={self.vk_id}{str_thread}'
        return url

    def __str__(self):
        max_length = 50
        text = str(self.text)
        if self.text is None or self.text == '':
            name = f'id={self.id}'
        elif len(text) > 50:
            name = text[1:max_length-3] + '...'
        else:
            name = text
        return '[DELETED] ' + name if self.is_deleted else name
