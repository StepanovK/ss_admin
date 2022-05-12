from peewee import *
from Models.base import BaseModel
from config import logger
import datetime


class User(BaseModel):
    id = PrimaryKeyField()
    first_name = CharField(100, default='', null=True)
    last_name = CharField(100, default='', null=True)
    city = CharField(100, default='', null=True)
    sex = CharField(10, null=True)
    birth_date = DateField(null=True)
    domain = CharField(100, default='')
    is_active = BooleanField(default=True)

    class Meta:
        table_name = 'users'

    def __str__(self):
        return self.chat_name()

    def chat_name(self):
        f_name = self.full_name()
        if f_name == '':
            return f'[id{self.id}]'
        else:
            return f'[id{self.id}|{f_name}]'

    def full_name(self):
        f_name = f'{self.last_name} {self.first_name}'
        return f_name.strip()
