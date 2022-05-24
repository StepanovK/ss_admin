from peewee import *
from BotVKPoster.PosterModels.base import BaseModel


class MessageOfSuggestedPost(BaseModel):
    message_id = IntegerField(primary_key=True)
    post_id = IntegerField(default=0)

    class Meta:
        table_name = 'messages_of_suggested_posts'
