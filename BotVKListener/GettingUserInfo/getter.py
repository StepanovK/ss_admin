from Models.Users import User
from config import logger


def show_user_info(vk_connection, peer_id: int):
    pass


def get_user_from_message(message_text: str):
    user_str = message_text
    if user_str.startswith('id'):
        user_str = user_str.replace('id', '')

    if user_str.isdigit():
        try:
            user = User.get(id=int(user_str))
            return user
        except User.DoesNotExist:
            pass

    if user_str.startswith('https://vk.com/'):
        user_str = user_str.replace('https://vk.com/', '')
    try:
        user = User.get(domain=user_str)
        return user
    except User.DoesNotExist:
        pass

    return None
