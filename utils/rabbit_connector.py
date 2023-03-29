import pika
import config
from utils.connection_holder import ConnectionsHolder


def send_message(message_type: str, message: str, rabbit_connection=None):
    connection = ConnectionsHolder().rabbit_connection if rabbit_connection is None else rabbit_connection
    if connection:
        channel = connection.channel()
        send_message_by_chanel(message_type, message, channel)
        if rabbit_connection is None:
            ConnectionsHolder().close_rabbit_connection()
        return True
    else:
        config.logger.warning(f'Failed connect to rabbit!')
        return False


def send_message_by_chanel(message_type: str, message: str, channel):
    queue_name = f'{config.queue_name_prefix}_{message_type}'
    channel.queue_declare(queue=queue_name,
                          durable=True)
    channel.basic_publish(exchange='',
                          routing_key=queue_name,
                          body=message.encode(),
                          properties=pika.BasicProperties(delivery_mode=2))


def get_messages(message_type: str, rabbit_connection=None):
    connection = ConnectionsHolder().rabbit_connection if rabbit_connection is None else rabbit_connection
    if connection:
        channel = connection.channel()
        messages = get_messages_from_chanel(message_type, channel)
        if rabbit_connection is None:
            ConnectionsHolder().close_rabbit_connection()
        return messages
    else:
        config.logger.warning(f'Failed connect to rabbit!')
        return []


def get_messages_from_chanel(message_type: str, channel):
    queue_name = f'{config.queue_name_prefix}_{message_type}'
    channel.queue_declare(queue=queue_name,
                          durable=True)
    messages = []
    while True:
        status, properties, message = channel.basic_get(queue=queue_name, auto_ack=True)
        if message is None:
            break
        else:
            message_text = message.decode()
            messages.append(message_text)

    return messages
