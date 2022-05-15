from peewee import *
from Models.base import BaseModel
from Models.Users import User


class UploadedFile(BaseModel):
    id = PrimaryKeyField()
    vk_id = IntegerField(null=True)
    type = CharField(25, default='')
    description = TextField(default='')
    preview_url = TextField(default='')
    url = TextField(default='')
    file_name = CharField(default='')
    user = ForeignKeyField(User, backref='uploaded_files', related_name='uploaded_files', null=True)
    date = DateTimeField(null=True)
    access_key = CharField(null=True)
    owner_id = CharField(50, null=True)
    platform = CharField(50, null=True)

    class Meta:
        table_name = 'uploaded_files'

    def __str__(self):
        return self.get_enum_format_name()

    def generate_file_name(self):
        self.file_name = self.get_enum_format_name()

    def get_enum_format_name(self):
        return f'{self.type}{self.owner_id}_{self.vk_id}'

    @staticmethod
    def available_types():
        return ['photo', 'video', 'audio', 'doc', 'page', 'poll']
