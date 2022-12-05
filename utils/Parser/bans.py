import datetime
from typing import Union
from Models.BanedUsers import BanedUser
from Models.Admins import get_admin_by_user
from .users import get_or_create_user


def parse_user_block(event, vk_connection=None) -> Union[BanedUser, None]:
    obj = event.object

    admin_user = get_or_create_user(vk_id=obj.admin_id, vk_connection=vk_connection)
    admin = get_admin_by_user(admin_user)
    user = get_or_create_user(vk_id=obj.user_id, vk_connection=vk_connection)

    new_record, created = BanedUser.get_or_create(user=user)
    if created or not admin.is_bot:  # При бане из админки возникает событие в апи и бан парсится повторно.
        new_record.admin = admin
    new_record.comment = obj.comment
    new_record.date = datetime.datetime.now()
    new_record.unblock_date = None if obj.unblock_date == 0 else datetime.datetime.fromtimestamp(obj.unblock_date)
    new_record.reason = obj.reason
    new_record.save()

    return new_record


def parse_user_unblock(event, vk_connection=None):
    obj = event.object
    user = get_or_create_user(vk_id=obj.user_id, vk_connection=vk_connection)

    BanedUser.delete().where(BanedUser.user == user).execute()
