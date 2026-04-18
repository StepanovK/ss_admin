from peewee import OperationalError, DatabaseError
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

    def table_exists(self, table_name):
        """Проверяет существование таблицы в базе данных"""
        try:
            # Для PostgreSQL
            cursor = self.db.execute_sql("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """, (table_name,))
            return cursor.fetchone()[0]
        except Exception:
            # Fallback: пробуем выполнить простой запрос
            try:
                self.db.execute_sql('SELECT 1 FROM "{}" LIMIT 1'.format(table_name))
                return True
            except Exception:
                return False

    def ensure_table(self, model):
        """Проверяет существование таблицы и создаёт её при необходимости"""
        table_name = model._meta.table_name
        migration_name = f"create_table_{table_name}"

        if self.is_migration_applied(migration_name):
            logger.debug(f"Table '{table_name}' already exists (migration applied)")
            return True

        # Проверяем существование таблицы напрямую
        if self.table_exists(table_name):
            logger.info(f"Table '{table_name}' already exists, marking migration as applied")
            self.mark_migration_applied(migration_name)
            return True

        # Создаём таблицу
        logger.info(f"Creating table '{table_name}'...")
        try:
            with self.db:
                self.db.create_tables([model], safe=True)
            self.mark_migration_applied(migration_name)
            logger.info(f"Table '{table_name}' created successfully")
            return True
        except Exception as ex:
            logger.error(f"Failed to create table '{table_name}': {ex}")
            return False

    def add_column_if_not_exists(self, table_name, column_name, column_definition):
        """
        Добавляет колонку в таблицу, если её нет

        Args:
            table_name: имя таблицы
            column_name: имя колонки
            column_definition: определение колонки (например, "VARCHAR(255) DEFAULT ''")
        """
        migration_name = f"add_column_{table_name}_{column_name}"

        if self.is_migration_applied(migration_name):
            logger.debug(f"Column '{column_name}' in '{table_name}' already exists")
            return True

        try:
            # Проверяем существование колонки
            cursor = self.db.execute_sql("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s AND column_name = %s
            """, (table_name, column_name))

            if cursor.fetchone():
                logger.info(f"Column '{column_name}' already exists in '{table_name}'")
                self.mark_migration_applied(migration_name)
                return True

            # Добавляем колонку
            self.db.execute_sql(
                "ALTER TABLE {} ADD COLUMN {} {}".format(table_name, column_name, column_definition)
            )
            self.mark_migration_applied(migration_name)
            logger.info(f"Column '{column_name}' added to '{table_name}'")
            return True

        except Exception as ex:
            logger.error(f"Failed to add column '{column_name}' to '{table_name}': {ex}")
            return False

    def add_index_if_not_exists(self, table_name, index_name, index_definition):
        """
        Добавляет индекс, если его нет

        Args:
            table_name: имя таблицы
            index_name: имя индекса
            index_definition: определение индекса (например, "(column1, column2)")
        """
        migration_name = f"add_index_{table_name}_{index_name}"

        if self.is_migration_applied(migration_name):
            logger.debug(f"Index '{index_name}' already exists")
            return True

        try:
            # Проверяем существование индекса
            cursor = self.db.execute_sql("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = %s AND indexname = %s
            """, (table_name, index_name))

            if cursor.fetchone():
                logger.info(f"Index '{index_name}' already exists")
                self.mark_migration_applied(migration_name)
                return True

            # Добавляем индекс
            self.db.execute_sql(
                "CREATE INDEX {} ON {} {}".format(index_name, table_name, index_definition)
            )
            self.mark_migration_applied(migration_name)
            logger.info(f"Index '{index_name}' added to '{table_name}'")
            return True

        except Exception as ex:
            logger.error(f"Failed to add index '{index_name}' to '{table_name}': {ex}")
            return False

    def run_migrations(self, migrations_list):
        """
        Запускает список миграций

        Args:
            migrations_list: список кортежей (функция_миграции, имя_миграции)
        """
        for migration_func, migration_name in migrations_list:
            if not self.is_migration_applied(migration_name):
                logger.info(f"Running migration: {migration_name}")
                try:
                    migration_func(self)
                    logger.info(f"Migration '{migration_name}' completed successfully")
                except Exception as ex:
                    logger.error(f"Migration '{migration_name}' failed: {ex}")
            else:
                logger.debug(f"Migration '{migration_name}' already applied, skipping")


# Глобальный экземпляр менеджера миграций
_migration_manager = None


def get_migration_manager(db):
    """Получает или создаёт экземпляр менеджера миграций"""
    global _migration_manager
    if _migration_manager is None or _migration_manager.db != db:
        _migration_manager = MigrationManager(db)
    return _migration_manager


def run_migrations(db):
    """Запускает все миграции"""
    manager = get_migration_manager(db)

    from Models.AppTokens import AppToken

    migrations = [
        (lambda m: m.ensure_table(AppToken), "create_table_app_tokens"),
        # Примеры будущих миграций:
        # (lambda m: m.add_column_if_not_exists('users', 'new_field', "VARCHAR(100) DEFAULT ''"), "add_new_field_to_users"),
        # (lambda m: m.add_index_if_not_exists('posts', 'idx_posts_date', "(date DESC)"), "add_index_posts_date"),
    ]

    manager.run_migrations(migrations)
    logger.info("All migrations completed")
