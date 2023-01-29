from . import users
from Models.Subscriptions import Subscription
from Models.Users import User
from datetime import datetime
from typing import Union


def parse_subscription(vk_event, vk_connection, is_subscribed=True, rewrite=False):
    user_id = vk_event.object.get('user_id', 0)
    group_id = vk_event.group_id
    return add_subscription(group_id=group_id,
                            user_id=user_id,
                            vk_connection=vk_connection,
                            is_subscribed=is_subscribed,
                            rewrite=rewrite)


def add_subscription(group_id, user_id: Union[User, int],
                     vk_connection, is_subscribed=True, subs_date=None, rewrite=False):
    if isinstance(user_id, User):
        user = user_id
    else:
        user = users.get_or_create_user(vk_id=user_id, vk_connection=vk_connection)

    subs_date = datetime.now() if subs_date is None else subs_date

    if user is not None:
        if rewrite:
            sub, created = Subscription.get_or_create(user=user,
                                                      group_id=group_id,
                                                      date=subs_date,
                                                      is_subscribed=is_subscribed)
        else:
            sub = Subscription.create(user=user,
                                      group_id=group_id,
                                      date=subs_date,
                                      is_subscribed=is_subscribed)
        return sub
