from peewee import *
from Models.base import BaseModel
from Models.Users import User


class Admin(BaseModel):
    id = PrimaryKeyField()
    user = ForeignKeyField(User, null=True, on_delete='SET NULL')
    tg_nickname = CharField(100, null=True)
    name = CharField(100, default='')
    is_bot = BooleanField(default=False)

    class Meta:
        table_name = 'admins'

    def __str__(self):
        if self.user is not None:
            st = str(self.user)
        elif self.name != '':
            st = self.name
        else:
            st = f'id{self.id}'

        return st
