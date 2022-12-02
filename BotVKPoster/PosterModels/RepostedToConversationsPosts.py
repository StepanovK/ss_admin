from peewee import *
from .base import BaseModel


class RepostedToConversationPost(BaseModel):
    post_id = CharField(100)
    conversation_id = CharField(100)
    conversation_message_id = CharField(100)

    class Meta:
        table_name = 'reposted_to_conversations_posts'
