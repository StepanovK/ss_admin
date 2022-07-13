from peewee import *
from .base import BaseModel


class SortedHashtag(BaseModel):
    post_id = CharField(100)
    hashtag = CharField(100)
    rating = FloatField(default=0)

    class Meta:
        table_name = 'sorted_hashtags'
        order_by = ['rating desc, id']

    def __str__(self):
        return self.hashtag
