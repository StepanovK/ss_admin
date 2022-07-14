from peewee import *
from Models.base import BaseModel
from Models.Users import User
from Models.Conversations import Conversation


class ConversationsMessage(BaseModel):
    id = CharField(100, primary_key=True)
    conversation = ForeignKeyField(Conversation)
    message_id = IntegerField(null=True, default=0)
    user = ForeignKeyField(User, on_delete='CASCADE', index=True, backref='posts', null=True)
    date = DateTimeField(formats=['%Y-%m-%d %H:%M:%S'], null=True)
    text = TextField(default='')
    from_group = BooleanField(default=False)
    is_edited = BooleanField(default=False)
    is_deleted = BooleanField(default=False)

    def __str__(self):
        url = self.get_url()
        return '[DELETED] ' + url if self.is_deleted else url

    class Meta:
        table_name = 'conversations_messages'
        order_by = ['conversation, date']

    def get_url(self):
        return self.generate_url(conversation=self.conversation, message_id=self.id)

    @classmethod
    def generate_id(cls, owner_id, conversation_id, message_id):
        return f'{owner_id}_{conversation_id}_{message_id}'

    @classmethod
    def generate_url(cls, conversation, message_id):
        conversation_url = conversation.get_url()
        url = f'{conversation_url}?post={message_id}'
        return url

