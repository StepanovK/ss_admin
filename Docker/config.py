from base_config import *

env = Env()
env.read_env()

db_host = 'postgres_ru'
db_port = 5432

rabbitmq_host = 'rabbitmq'

debug = bool(env.int("debug"))
