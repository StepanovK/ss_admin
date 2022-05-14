from peewee import *
from Models.base import BaseModel
from Models.Users import User


class Admin(BaseModel):
    id = PrimaryKeyField()
    user = ForeignKeyField(User, null=True, on_delete='SET NULL')
    tg_nickname = CharField(100, null=True)
    name = CharField(100, default='')

    class Meta:
        table_name = 'admins'

    def __str__(self):
        return self.name if self.name != '' else f'id{self.id}'
