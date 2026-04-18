from peewee import OperationalError

from Models.AppTokens import AppToken
from config import logger


class MigrationManager:
    """Универсальный менеджер миграций"""

    def __init__(self, db):
        self.db = db
        self.migrations_table = '_migrations_history'
        self._ensure_migrations_table()

    def _ensure_migrations_table(self):
        """Создаёт таблицу истории миграций если её нет"""
        try:
            self.db.execute_sql("""
                CREATE TABLE IF NOT EXISTS {} (
                    id SERIAL PRIMARY KEY,
                    migration_name VARCHAR(255) UNIQUE NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """.format(self.migrations_table))
            logger.debug("Migrations table ensured")
        except Exception as ex:
            logger.error(f"Failed to create migrations table: {ex}")

    def is_migration_applied(self, migration_name):
        """Проверяет, была ли применена миграция"""
        try:
            cursor = self.db.execute_sql(
                "SELECT 1 FROM {} WHERE migration_name = %s".format(self.migrations_table),
                (migration_name,)
            )
            return cursor.fetchone() is not None
        except Exception as ex:
            logger.error(f"Failed to check migration {migration_name}: {ex}")
            return False

    def mark_migration_applied(self, migration_name):
        """Отмечает миграцию как применённую"""
        try:
            self.db.execute_sql(
                "INSERT INTO {} (migration_name) VALUES (%s)".format(self.migrations_table),
                (migration_name,)
            )
            logger.info(f"Migration '{migration_name}' marked as applied")
        except Exception as ex:
            logger.error(f"Failed to mark migration {migration_name}: {ex}")

    def ensure_table(self, model):
        """Проверяет существование таблицы и создаёт её при необходимости"""
        table_name = model._meta.table_name
        migration_name = f"create_table_{table_name}"

        if self.is_migration_applied(migration_name):
            logger.debug(f"Table '{table_name}' already exists (migration applied)")
            return True

        try:
            with self.db:
                model.select().limit(1).exists()
            logger.info(f"Table '{table_name}' already exists, marking migration as applied")
            self.mark_migration_applied(migration_name)
            return True
        except OperationalError as e:
            if 'no such table' in str(e).lower() or 'does not exist' in str(e).lower():
                logger.info(f"Creating table '{table_name}'...")
                with self.db:
                    self.db.create_tables([model], safe=True)
                self.mark_migration_applied(migration_name)
                logger.info(f"Table '{table_name}' created successfully")
                return True
            else:
                logger.error(f"Error checking table '{table_name}': {e}")
                return False

    def run_all_migrations(self):
        """Запускает все миграции"""
        migrations = [
            (lambda m: m.ensure_table(AppToken), "create_table_app_tokens"),
            # Примеры будущих миграций:
            # (lambda m: m.add_column_if_not_exists('users', 'new_field', "VARCHAR(100) DEFAULT ''"), "add_new_field_to_users"),
            # (lambda m: m.add_index_if_not_exists('posts', 'idx_posts_date', "(date DESC)"), "add_index_posts_date"),
        ]

        for migration_func, migration_name in migrations:
            if not self.is_migration_applied(migration_name):
                logger.info(f"Running migration: {migration_name}")
                try:
                    migration_func(self)
                    logger.info(f"Migration '{migration_name}' completed successfully")
                except Exception as ex:
                    logger.error(f"Migration '{migration_name}' failed: {ex}")
            else:
                logger.debug(f"Migration '{migration_name}' already applied, skipping")

        logger.info("All migrations completed")


# Глобальный экземпляр
_migration_manager = None


def run_migrations(db):
    """Упрощённая функция для запуска миграций"""
    global _migration_manager
    if _migration_manager is None or _migration_manager.db != db:
        _migration_manager = MigrationManager(db)
    _migration_manager.run_all_migrations()
