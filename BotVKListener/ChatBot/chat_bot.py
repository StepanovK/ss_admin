from .commander import Commander
from utils.connection_holder import ConnectionsHolder
import config
import os

dir_name = os.path.dirname(os.path.abspath(__file__))
keyboard_path = os.path.join(dir_name, 'keyboards/keyboard.json')
none_keyboard_path = os.path.join(dir_name, 'keyboards/none.json')


class ChatBot:
    def __init__(self):
        self._vk = ConnectionsHolder().vk_connection_group
        self._vk_admin = ConnectionsHolder().vk_connection_admin
        self.users = {}
        self.user_call_admin = None

    def send_msg(self, random_id, send_id, message,
                 keyboard=open(keyboard_path, "r", encoding="UTF-8").read(),
                 attachment=None):
        """
        Отправка сообщения через метод messages.send
        :param attachment: вложение
        :param random_id: random_id для отправки сообщений
        :param keyboard: клавиатура, возвращаемая пользователю
        :param send_id: vk id пользователя, который получит сообщение
        :param message: содержимое отправляемого письма
        :return: None
        """
        # print("отправка сообщения")
        return self._vk.messages.send(peer_id=send_id,
                                      message=message,
                                      random_id=random_id,
                                      keyboard=keyboard,
                                      attachment=attachment)

    def chat(self, event):
        if event.object.message.get("from_id") not in self.users:
            self.users[event.object.message.get("from_id")] = Commander()
        # Пришло новое сообщение
        # print('Написали в ЛС')
        answer = self.users[event.object.message.get("from_id")].input(event.object.message.get("text"))
        if event.object.message.get("text") == "Начать":
            self.send_msg(event.object.message.get("random_id"), event.object.message.get("peer_id"),
                          "Привет, {}!\nЯ бот группы Солнечная Сортировка!"
                          .format(self._vk.users.get(user_id=event.object.message.get("from_id"))[0]['first_name']),
                          self.users[event.object.message.get("from_id")].now_keyboard)
        elif event.object.message.get("text") == "Позвать администратора":
            self.send_msg(event.object.message.get("random_id"), event.object.message.get("peer_id"),
                          answer,
                          self.users[event.object.message.get("from_id")].now_keyboard,
                          self.users[event.object.message.get("from_id")].now_attachment)
            msg_url = 'https://vk.ru/gim{}?sel={}'.format(config.group_id, event.object.message.get("peer_id"))
            if event.object.message.get("peer_id") != self.user_call_admin:
                self.send_msg(event.object.message.get("random_id"), config.chat_for_alarm,
                              'Админы, Вас там зовут!!!\n{}'.format(msg_url),
                              keyboard=open(none_keyboard_path, "r", encoding="UTF-8").read())
                self.user_call_admin = event.object.message.get("peer_id")

        elif answer is not None:
            self.send_msg(event.object.message.get("random_id"), event.object.message.get("peer_id"),
                          answer,
                          self.users[event.object.message.get("from_id")].now_keyboard,
                          self.users[event.object.message.get("from_id")].now_attachment)
