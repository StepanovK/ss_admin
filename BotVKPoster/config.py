from environs import Env
import loguru

logger = loguru.logger
logger.add('Logs/bot_log.log', format='{time} {level} {message}', rotation='512 KB', compression='zip')

env = Env()
env.read_env()

group_id = env.int("group_id")
group_token = env.str("group_token")
admin_token = env.str("admin_token")
admin_phone = env.str("admin_phone")
admin_pass = env.str("admin_pass")
chat_for_suggest = env.int("chat_for_suggest")

db_host = env.str("db_host")
db_port = env.int("db_port")
db_user = env.str("db_user")
db_password = env.str("db_password")
db_name = env.str("db_name")

rabbitmq_host = env.str("rabbitmq_host")
rabbitmq_port = env.int("rabbitmq_port")
queue_name_prefix = env.str("queue_name_prefix")

config_db = {
    'db_host': db_host,
    'db_port': db_port,
    'db_user': db_user,
    'db_password': db_password,
    'db_name': db_name,
}