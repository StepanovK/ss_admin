from peewee import *
from Models.base import BaseModel
from Models.Users import User
from typing import Optional


class Subscription(BaseModel):
    group_id = IntegerField(null=True)
    user = ForeignKeyField(User, backref='subscriptions')
    date = DateTimeField(formats=['%Y-%m-%d'], null=True)
    is_subscribed = BooleanField(default=True)

    class Meta:
        table_name = 'subscriptions'

    def __str__(self):
        state = 'ПОДПИСАН' if self.is_subscribed else 'ОТПИСАН'
        date_sub = 'Неизвестно когда' if self.date is None else f'{self.date:%Y-%m-%d}'
        return f'{date_sub} {state}'

    @classmethod
    def get_slise_of_last(cls, is_subscribed: Optional[bool] = None) -> dict:
        _SA = Subscription.alias('SA')
        max_dates = (_SA.select(
            _SA.user_id,
            fn.Max(_SA.date).alias('date')
        ).group_by(_SA.user).alias('max_dates'))

        slise_query = (Subscription.select(
            Subscription.user,
            Subscription.date,
            Subscription.is_subscribed).join(
            max_dates, on=(
                    (max_dates.c.user_id == Subscription.user_id) &
                    (max_dates.c.date == Subscription.date))
        )
        ).join(User, on=(Subscription.user == User.id)).order_by(User.last_name,
                                                                 User.first_name).execute()

        slise = {}
        for row in slise_query:
            if is_subscribed is not None and row.is_subscribed != is_subscribed:
                continue

            slise[row.user] = {
                'is_subscribed': row.is_subscribed,
                'date': row.date,
            }

        return slise
