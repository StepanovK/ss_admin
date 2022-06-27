from peewee import *
from .base import BaseModel


class SortedHashtag(BaseModel):
    post_id = CharField(100)
    hashtag = CharField(100)

    class Meta:
        table_name = 'sorted_hashtags'
        order_by = ['id']
