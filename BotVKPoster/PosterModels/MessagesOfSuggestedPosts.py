from peewee import *
from .base import BaseModel


class MessageOfSuggestedPost(BaseModel):
    post_id = CharField(100, primary_key=True)
    message_id = IntegerField(null=True)

    class Meta:
        table_name = 'messages_of_suggested_posts'
