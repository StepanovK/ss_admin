from . import users
from Models.Subscriptions import Subscription
from datetime import datetime


def parse_subscription(vk_event, vk_connection, is_subscribed=True):
    user_id = vk_event.object.get('user_id', 0)
    group_id = vk_event.group_id
    return add_subscription(group_id, user_id, vk_connection, is_subscribed)


def add_subscription(group_id, user_id, vk_connection, is_subscribed=True, subs_date=None):
    user = users.get_or_create_user(vk_id=user_id, vk_connection=vk_connection)
    subs_date = datetime.now() if subs_date is None else subs_date
    if user is not None:
        sub = Subscription.create(user=user,
                                  group_id=group_id,
                                  date=subs_date,
                                  is_subscribed=is_subscribed)
        return sub
