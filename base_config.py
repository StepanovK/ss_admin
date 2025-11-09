from environs import Env
import loguru

logger = loguru.logger
logger.add('Logs/bot_log.log', format='{time} {level} {message}', rotation='512 KB', compression='zip')

VK_URL = 'https://vk.ru/'
MAX_MESSAGE_SIZE = 4048

env = Env()
env.read_env()

group_id = env.int("group_id")
group_token = env.str("group_token")
group_token_poster = env.str("group_token_poster")
admin_token = env.str("admin_token")
admin_phone = env.str("admin_phone")
admin_pass = env.str("admin_pass")

chat_for_suggest = env.int("chat_for_suggest")
chat_for_alarm = env.int("chat_for_alarm")  # Уведомления из ЛК СС
chat_for_comments_check = env.int("chat_for_comments_check", 0)  # Уведомления о подозрительных комментах
advertising_conversation_id = env.int("advertising_conversation_id", 0)

db_host = 'localhost'
db_port = env.int("POSTGRES_PORT", 5432)
db_user = env.str("POSTGRES_USER")
db_password = env.str("POSTGRES_PASSWORD")
db_name = 'admin_ss'

rabbitmq_host = 'localhost'
rabbitmq_port = 5672
queue_name_prefix = 'vk_events'

# for Google Tables
secret_key_google = env.str("secret_google")
spreadsheetId = env.str("spreadsheetId")

domain = env.str("domain")
# for TG sender
telegram = dict(
    api_id=env.int("api_id"),
    api_hash=env.str("api_hash"),
    bot_token=env.str("bot_token"),
)
channel = env.int("channel")

# for dynamic title
token_weather = env.str("token_weather")

openai_token = env.str("openai_token")
enable_openai = openai_token.strip() != ''

# healthcheck
healthcheck_interval = env.int("healthcheck_interval")
healthcheck_timeout = env.int("healthcheck_timeout")
healthcheck_chat_id = env.int("healthcheck_chat_id")
healthcheck_queue_name_prefix = 'healthcheck'

days_for_checking_messages_of_suggested_posts = 30
time_to_update_messages_of_suggested_posts = 1 * (24 * 60 * 60) - 60
