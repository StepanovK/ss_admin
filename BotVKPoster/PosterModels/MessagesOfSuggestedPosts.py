from peewee import *
from .base import BaseModel


class MessageOfSuggestedPost(BaseModel):
    post_id = CharField(100)
    message_id = IntegerField(null=True)
    message_date = DateTimeField(null=True)

    class Meta:
        table_name = 'messages_of_suggested_posts'
