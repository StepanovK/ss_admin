from peewee import *
from BotVKPoster.PosterModels.base import BaseModel


class PublishedPost(BaseModel):
    suggested_post_id = CharField(100)
    published_post_id = CharField(100)
    admin_id = IntegerField(null=True)

    class Meta:
        table_name = 'published_posts'
