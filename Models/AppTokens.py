from peewee import *
from Models.base import BaseModel
import datetime


class AppToken(BaseModel):
    """Модель для хранения токенов доступа"""
    id = PrimaryKeyField()
    token_type = CharField(50, unique=True)  # 'master' - основной токен админа
    access_token = TextField()
    refresh_token = TextField(null=True)
    expires_at = DateTimeField(null=True)
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = 'app_tokens'

    @classmethod
    def get_master_token(cls):
        """Получить актуальный мастер-токен"""
        try:
            token_record = cls.get(token_type='master')
            return token_record
        except cls.DoesNotExist:
            return None

    @classmethod
    def update_token(cls, access_token, refresh_token=None, expires_in=None):
        """Обновить токен в БД"""
        token_record, created = cls.get_or_create(token_type='master')
        token_record.access_token = access_token
        token_record.updated_at = datetime.datetime.now()

        if refresh_token:
            token_record.refresh_token = refresh_token

        if expires_in:
            token_record.expires_at = datetime.datetime.now() + datetime.timedelta(seconds=expires_in)

        token_record.save()
        return token_record

    def is_expired(self):
        """Проверить, истёк ли токен"""
        if not self.expires_at:
            return False
        # Добавляем буфер в 5 секунд для безопасности
        buffer = datetime.timedelta(seconds=5)
        return datetime.datetime.now() + buffer >= self.expires_at

    def seconds_until_expiry(self):
        """Сколько секунд осталось до истечения токена"""
        if not self.expires_at:
            return 3600  # По умолчанию час, если нет информации
        delta = self.expires_at - datetime.datetime.now()
        return max(0, delta.total_seconds())