import datetime

from Models.BanedUsers import BanedUser
from Models.Admins import get_admin_by_user
from .users import get_or_create_user


def parse_user_block(event, vk_connection=None):
    obj = event.object
    admin_user = get_or_create_user(vk_id=obj.admin_id, vk_connection=vk_connection)
    user = get_or_create_user(vk_id=obj.user_id, vk_connection=vk_connection)

    new_record, _ = BanedUser.get_or_create(user=user)
    new_record.admin = get_admin_by_user(admin_user)
    new_record.date = datetime.datetime.now()
    new_record.reason = obj.reason
    new_record.comment = obj.comment
    new_record.save()

    return new_record


def parse_user_unblock(event, vk_connection=None):
    obj = event.object
    user = get_or_create_user(vk_id=obj.user_id, vk_connection=vk_connection)

    BanedUser.delete().where(BanedUser.user == user).execute()
