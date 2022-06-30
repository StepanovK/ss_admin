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

db_host = 'postgres_ru'
db_port = 5432
db_user = env.str("POSTGRES_USER")
db_password = env.str("POSTGRES_PASSWORD")
db_name = 'admin_ss'

rabbitmq_host = 'rabbitmq'
rabbitmq_port = 5672
queue_name_prefix = 'vk_events'

# for Google Tables
secret_key_google = env.str("secret_google")
spreadsheetId = env.str("spreadsheetId")
