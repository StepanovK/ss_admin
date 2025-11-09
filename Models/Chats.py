from peewee import *

from Models.base import BaseModel
from config import VK_URL

SHIFT_CHAT_ID = 2000000000


class Chat(BaseModel):
    id = CharField(100, primary_key=True)
    owner_id = IntegerField(null=True)
    chat_id = IntegerField(null=True)
    title = CharField(default='')
    url = CharField(default='')
    private = BooleanField(default=False)
    is_deleted = BooleanField(default=False)

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

    def get_url(self) -> str:
        if isinstance(self.owner_id, int) and isinstance(self.chat_id, int):
            owner_id = abs(self.owner_id)
            short_id = self.chat_id - SHIFT_CHAT_ID
            return f'{VK_URL}gim{owner_id}?sel=c{short_id}'
        return ''

    @classmethod
    def generate_id(cls, owner_id, chat_id):
        return f'{owner_id}_{chat_id}'
