from environs import Env
import loguru

logger = loguru.logger
logger.add('Logs/bot_log.log', format='{time} {level} {message}', rotation='512 KB', compression='zip')

env = Env()
env.read_env()

telegram_bot_token = env.str("telegram_bot_token")
telegram_chat_id = env.int("telegram_chat_id")

db_host = env.str("db_host")
db_port = env.int("db_port")
db_user = env.str("db_user")
db_password = env.str("db_password")
db_name = env.str("db_name")

config_db = {
    'db_host': db_host,
    'db_port': db_port,
    'db_user': db_user,
    'db_password': db_password,
    'db_name': db_name,
}