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
    def update_token(cls, access_token, refresh_token=None, expires_in=None, expires_at=None):
        """Обновить токен в БД"""
        token_record, created = cls.get_or_create(token_type='master')
        token_record.access_token = access_token
        token_record.updated_at = datetime.datetime.now()

        if refresh_token:
            token_record.refresh_token = refresh_token

        if expires_in:
            token_record.expires_at = datetime.datetime.now() + datetime.timedelta(seconds=expires_in)
        elif expires_at:
            if isinstance(expires_at, str):
                token_record.expires_at = datetime.datetime.fromisoformat(expires_at)
            else:
                token_record.expires_at = expires_at

        token_record.save()
        return token_record

    def is_expired(self, buffer_minutes=5):
        """Проверить, истёк ли токен (с буфером)"""
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

    @classmethod
    def init_from_env(cls):
        """Инициализирует токен из переменных окружения (при первом запуске)"""
        import config

        # Проверяем, есть ли уже токен в БД
        existing = cls.get_master_token()
        if existing:
            config.logger.info("Token already exists in database")
            return existing

        # Пытаемся загрузить из .env
        if config.admin_access_token:
            config.logger.info("Loading admin token from .env file")

            expires_at = None
            if config.admin_token_expires_at:
                try:
                    expires_at = datetime.datetime.fromisoformat(config.admin_token_expires_at)
                except:
                    config.logger.warning(f"Invalid expires_at format: {config.admin_token_expires_at}")

            return cls.update_token(
                access_token=config.admin_access_token,
                refresh_token=config.admin_refresh_token,
                expires_at=expires_at
            )
        else:
            config.logger.warning("No admin token found in .env file! Some features may not work.")
            return None