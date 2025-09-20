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

    VK_LINK = 'https://vk.ru/'

    class Meta:
        table_name = 'private_messages'
        indexes = ['user', 'admin']
        order_by = ['id, date']

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

    def get_chat_url(self):
        return f'{self.VK_LINK}gim{group_id}?sel={self.chat_id}'

    @classmethod
    def generate_id(cls, chat_id, message_id):
        return f'{chat_id}_{message_id}'

    @classmethod
    def it_is_private_chat(cls, chat_id: int):
        public_chat_ids = 2000000000
        is_private = isinstance(chat_id, int) and chat_id < public_chat_ids
        return is_private

