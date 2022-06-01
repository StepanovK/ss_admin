from peewee import *

db = SqliteDatabase('PosterModels/posting_statuses.sqlite')


class BaseModel(Model):
    class Meta:
        database = db
