from peewee import *
from Models.base import BaseModel
from Models.Users import User


class Subscription(BaseModel):
    group = IntegerField(null=True)
    user = ForeignKeyField(User, backref='subscriptions', related_name='subscriptions')
    date = DateTimeField(formats=['%Y-%m-%d %H:%M:%S'], null=True)
    is_subscribed = BooleanField(default=True)

    class Meta:
        table_name = 'subscriptions'
