from peewee import *
from Models.base import BaseModel


class Chat(BaseModel):
    id = CharField(100, primary_key=True)
    owner_id = IntegerField(null=True)
    chat_id = IntegerField(null=True)
    title = CharField(default='')
    url = CharField(default='')
    private = BooleanField(default=False)
    is_deleted = BooleanField(default=False)

    VK_LINK = 'https://vk.com/'

    def __str__(self):
        if self.title is not None and self.title != '':
            name = self.title
        elif self.url is not None and self.url != '':
            name = self.url
        else:
            name = str(self.id)
        return '[DELETED] ' + name if self.is_deleted else name

    class Meta:
        table_name = 'chats'

    @classmethod
    def generate_id(cls, owner_id, chat_id):
        return f'{owner_id}_{chat_id}'

