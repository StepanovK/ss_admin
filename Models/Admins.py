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
            st = f'@id{self.id}'

        return st


def get_admin_by_vk_id(user_id: int) -> Admin:
    user, _ = User.get_or_create(id=user_id)
    return get_admin_by_user(user)


def get_admin_by_user(user: User) -> Admin:
    admin, created = Admin.get_or_create(user=user)
    if created:
        admin.name = user.full_name()
        admin.save()
    return admin
