from environs import Env
import loguru

logger = loguru.logger
logger.add('Logs/Models.log', format='{time} {level} {message}', rotation='512 KB', compression='zip')

env = Env()
env.read_env()

db_host = env.str("db_host")
db_port = env.int("db_port")
db_user = env.str("db_user")
db_password = env.str("db_password")
db_name = env.str("db_name")
