from peewee import *
from Models.base import BaseModel
from Models.Users import User
from Models.Admins import Admin

BAN_REASONS = {
    1: 'спам',
    2: 'оскорбление участников',
    3: 'нецензурные выражения',
    4: 'сообщения не по теме',
    0: 'другое',
}

REPORT_TYPES_BY_BAN_REASONS = {
    1: 'spam',
    2: 'insult',
    3: 'insult',
}


class BanedUser(BaseModel):
    user = ForeignKeyField(User)
    date = DateTimeField(null=True, formats=['%Y-%m-%d %H:%M:%S'])
    reason = IntegerField(null=True)
    admin = ForeignKeyField(Admin, null=True)
    report_type = CharField(30, default='')
    comment = CharField(255, default='')

    class Meta:
        table_name = 'baned_users'

    def __str__(self):
        date_str = 'давно' if self.date is None else str(self.date)
        reason_str = '' if self.reason is None else f' за {BAN_REASONS.get(self.reason)}'
        return f'{self.user} ({date_str}{reason_str})'