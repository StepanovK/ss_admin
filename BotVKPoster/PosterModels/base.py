from peewee import *

db = SqliteDatabase('posting_statuses.sqlite')


class BaseModel(Model):
    class Meta:
        database = db
