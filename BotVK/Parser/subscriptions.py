from BotVK.Parser import users
from Models.Subscriptions import Subscription
from datetime import datetime


def parse_subscription(vk_event, vk_connection, is_subscribed=True):
    user_id = vk_event.object.get('user_id', 0)
    group_id = vk_event.group_id
    user = users.get_or_create_user(vk_id=user_id, vk_connection=vk_connection)
    if user is not None:
        sub = Subscription.create(user=user,
                                  group_id=group_id,
                                  date=datetime.now(),
                                  is_subscribed=is_subscribed)
        return sub
