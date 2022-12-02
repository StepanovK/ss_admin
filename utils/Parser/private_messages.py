from Models.PrivateMessages import PrivateMessage
from Models.Admins import Admin
from . import users
from . import attachments
import datetime


def parse_private_message(vk_object: dict, vk_connection=None):
    chat_id = vk_object.get('peer_id')
    message_vk_id = vk_object.get('id')
    message_id = PrivateMessage.generate_id(chat_id=chat_id, message_id=message_vk_id)

    message, created = PrivateMessage.get_or_create(id=message_id)
    message.chat_id = chat_id
    message.date = datetime.datetime.fromtimestamp(vk_object.get('date', 0)),
    message.message_id = message_vk_id
    message.text = vk_object.get('text', '')
    message.user = users.get_or_create_user(chat_id, vk_connection)

    from_id = vk_object.get('from_id')
    if from_id != chat_id:
        admin_user_id = vk_object.get('admin_author_id', from_id)
        admin_user = users.get_or_create_user(admin_user_id, vk_connection)
        admin, admin_created = Admin.get_or_create(user=admin_user)
        message.admin = admin

    message.save()

    attachments.parce_added_attachments(attachment_object=message,
                                        attachments=vk_object.get('attachments', []),
                                        user=message.user if message.admin is None else message.admin.user)

    return message
