from peewee import *
from base import BaseModel
from Users import User


class Attachment(BaseModel):
    id = IntegerField(unique=True, primary_key=True)
    type = CharField(max_length=100, default='')
    description = TextField()
    preview_url = TextField()
    url = TextField()
    file_name = CharField()
    user_id = ForeignKeyField(User)

    class Meta:
        table_name = 'attachments'
        primary_key = 'id'
