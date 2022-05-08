from peewee import *
from base import BaseModel
from Users import User


class Subscription(BaseModel):
    user = ForeignKeyField(User, backref='subscriptions', related_name='subscriptions')
    date = DateTimeField(formats=['%Y-%m-%d %H:%M:%S'])
    is_subscribed = BooleanField()

    class Meta:
        table_name = 'subscriptions'
