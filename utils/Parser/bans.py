import datetime
from typing import Union
from Models.BanedUsers import BanedUser
from Models.Admins import get_admin_by_user
from .users import get_or_create_user


def parse_user_block(vk_ban, vk_connection=None) -> Union[BanedUser, None]:

    admin_user = get_or_create_user(vk_id=vk_ban['admin_id'], vk_connection=vk_connection)
    admin = get_admin_by_user(admin_user)
    user = get_or_create_user(vk_id=vk_ban['user_id'], vk_connection=vk_connection)

    new_record, created = BanedUser.get_or_create(user=user)
    if created or not admin.is_bot:  # При бане из админки возникает событие в апи и бан парсится повторно.
        new_record.admin = admin
    new_record.comment = vk_ban['comment']
    if 'date' in vk_ban:
        new_record.date = datetime.datetime.fromtimestamp(vk_ban['date'])
    else:
        new_record.date = datetime.datetime.now()
    new_record.unblock_date = None if vk_ban['unblock_date'] == 0 \
        else datetime.datetime.fromtimestamp(vk_ban['unblock_date'])
    new_record.reason = vk_ban['reason']
    new_record.save()

    return new_record


def parse_user_unblock(vk_ban, vk_connection=None):
    user = get_or_create_user(vk_id=vk_ban.user_id, vk_connection=vk_connection)

    BanedUser.delete().where(BanedUser.user == user).execute()
