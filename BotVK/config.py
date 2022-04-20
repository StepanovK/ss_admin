from environs import Env
import loguru

logger = loguru.logger
logger.add('Logs/bot_log.log', format='{time} {level} {message}', rotation='512 KB', compression='zip')

env = Env()
env.read_env()

group_name = env.str("group_name")
group_id = env.int("group_id")
group_token = env.str("group_token")
telegram_bot_token = env.str("telegram_bot_token")
telegram_chat_id = env.int("telegram_chat_id")
