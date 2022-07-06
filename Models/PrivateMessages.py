from Models.base import BaseModel
from Models.Users import User
from Models.Admins import Admin
from peewee import *
from config import group_id


class PrivateMessage(BaseModel):
    id = CharField(primary_key=True)
    date = DateTimeField(formats=['%Y-%m-%d %H:%M:%S'], null=True)
    user = ForeignKeyField(User, null=True, on_delete='CASCADE', index=True, backref='private_messages')
    admin = ForeignKeyField(Admin, null=True, on_delete='CASCADE', index=True, backref='private_messages')
    text = TextField(default='')
    chat_id = IntegerField(null=True)
    message_id = IntegerField(null=True)
    is_deleted = BooleanField(default=False)

    VK_LINK = 'https://vk.com/'

    class Meta:
        table_name = 'private_messages'
        indexes = ['user', 'admin']
        order_by = ['id, date']

    def get_chat_url(self):
        return f'{self.VK_LINK}gim{group_id}?sel={self.chat_id}'

    @classmethod
    def generate_id(cls, chat_id, message_id):
        return f'{chat_id}_{message_id}'
