import pytest
from peewee import *

from Models import base
from Models import create_db

DB_NAME = 'temp_db.sqlite'


@pytest.fixture(scope="module")
def test_db(monkeypatch):

    db = SqliteDatabase(DB_NAME)
    monkeypatch.setattr('base.BaseModel.Meta.database', db)

    create_db()
    add_test_data()
    yield
    remove_db()


def create_db():
    print('DB created')
    # Models.create_db.create_all_tables()


def add_test_data():
    print('Test data added')
    pass


def remove_db():
    print('DB removed')
    pass
