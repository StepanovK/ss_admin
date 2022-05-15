from peewee import *
from Models.base import BaseModel
from Models.Users import User


class Subscriber(BaseModel):
    group = IntegerField(null=True)
    user = ForeignKeyField(User, backref='subscriptions')
    date = DateTimeField(formats=['%Y-%m-%d'], null=True)
    is_subscribed = BooleanField(default=True)

    class Meta:
        table_name = 'subscribers'

    def __str__(self):
        state = 'ПОДПИСАН' if self.is_subscribed else 'ОТПИСАН'
        return f'{self.group} от {self.date} {state}'
