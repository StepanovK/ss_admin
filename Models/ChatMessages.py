from peewee import *
from Models.base import BaseModel
from Models.Users import User
from Models.Chats import Chat


class ChatMessage(BaseModel):
    id = CharField(100, primary_key=True)
    chat = ForeignKeyField(Chat)
    message_id = IntegerField(null=True, default=0)
    replied_message = ForeignKeyField('self', null=True)
    user = ForeignKeyField(User, on_delete='CASCADE', index=True, backref='posts', null=True)
    from_group = BooleanField(default=False)
    date = DateTimeField(formats=['%Y-%m-%d %H:%M:%S'], null=True)
    text = TextField(default='')

    def __str__(self):
        max_length = 50
        text = str(self.text)
        if self.text is None or text == '':
            name = f'id={self.chat}_{self.id}'
        elif len(text) > 50:
            name = text[1:max_length - 3] + '...'
        else:
            name = text
        return name

    class Meta:
        table_name = 'chat_messages'
        order_by = ['chat, date']

    @classmethod
    def generate_id(cls, message_id, chat=None, owner_id=None, chat_id=None):
        if chat is None:
            return f'{owner_id}_{chat_id}_{message_id}'
        else:
            return f'{chat.id}_{message_id}'
