from environs import Env
import loguru
import json

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
hashtags = sorted(json.loads(env.str("hashtags")))

db_host = env.str("POSTGRES_HOST")
db_port = env.int("POSTGRES_PORT")
db_user = env.str("POSTGRES_USER")
db_password = env.str("POSTGRES_PASSWORD")
db_name = env.str("POSTGRES_DB")

rabbitmq_host = env.str("RABBITMQ_DEFAULT_HOST")
rabbitmq_port = env.int("RABBITMQ_DEFAULT_PORT")
queue_name_prefix = env.str("queue_name_prefix")

# for Google Tables
secret_key_google = env.str("secret_google")
spreadsheetId = env.str("spreadsheetId")