from peewee import *
from base import BaseModel


class User(BaseModel):
    id = IntegerField(unique=True, primary_key=True)
    first_name = CharField(default='', null=True)
    last_name = CharField(default='', null=True)
    city = CharField(default='', null=True)
    birth_date = DateField()
    is_active = BooleanField(null=True)

    class Meta:
        table_name = 'users'
