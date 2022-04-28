from peewee import *
import config

psql_db = PostgresqlDatabase(database=config.db_name, user=config.db_user, password=config.db_password,
                             host=config.db_host, port=config.db_port)


class BaseModel(Model):
    class Meta:
        database = psql_db
