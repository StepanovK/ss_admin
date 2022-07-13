from peewee import *
from Models.base import BaseModel


class Conversation(BaseModel):
    id = CharField(100, primary_key=True)
    owner_id = IntegerField(null=True, default=0)
    conversation_id = IntegerField(null=True, default=0)
    title = CharField(default='')
    text = TextField(default='')
    date_of_creating = DateField(null=True)
    days_for_cleaning = IntegerField(default=0)
    is_deleted = BooleanField(default=False)
    is_closed = BooleanField(default=False)

    VK_LINK = 'https://vk.com/'

    def __str__(self):
        if self.title is None or self.title == '':
            return self.get_url()
        else:
            return self.title

    class Meta:
        table_name = 'conversations'
        order_by = ['id']

    def get_url(self):
        url = f'{self.VK_LINK}topic{self.owner_id}_{self.conversation_id}'
        return url

    @classmethod
    def generate_id(cls, owner_id, conversation_id):
        return f'{owner_id}_{conversation_id}'

