# Перечисления команд, режимов
import pymorphy2
import config

from .command_enum import Command
from utils.connection_holder import ConnectionsHolder
from .mode_enum import Mode
from functools import lru_cache
import os

dir_name = os.path.dirname(os.path.abspath(__file__))
keyboard_path = os.path.join(dir_name, 'keyboards/keyboard.json')


class Commander:

    def __init__(self):

        # Текущий, предыдущий режимы
        self.now_mode = Mode.default
        self.last_mode = Mode.default
        self._vk = ConnectionsHolder().vk_connection_group
        self._vk_admin = ConnectionsHolder().vk_connection_admin

        self.last_command = None
        self.now_keyboard = open(keyboard_path, "r", encoding="UTF-8").read()
        self.last_keyboard = open(keyboard_path, "r", encoding="UTF-8").read()
        self.now_attachment = None
        self.last_attachment = None
        # Для запомминания ответов пользователя
        self.last_ans = None
        self.user_info = False
        self.calculationAdvertising = {'photo': None, 'firm': None, 'pin': None, 'day_of_pin': None, 'del': None}

    def change_keyboard(self, to_keyboard):
        """
        Меняет клавиатуру пользователя
        :param to_keyboard: Измененная клавиатура
        """
        self.last_keyboard = self.now_keyboard
        self.now_keyboard = to_keyboard

    def change_attachment(self, to_attachment):
        """
        Меняет вложение пользователя
        :param to_attachment:
        """
        self.last_attachment = self.now_attachment
        self.now_attachment = to_attachment

    def change_mode(self, to_mode):
        """
        Меняет режим приема команд
        :param to_mode: Измененный мод
        """
        self.last_mode = self.now_mode
        self.now_mode = to_mode

        self.last_ans = None

    def f_tokenizer(self, s):
        morph = pymorphy2.MorphAnalyzer()
        t = s.split(' ')
        f = []
        for j in t:
            m = morph.parse(
                j.replace('.', '').replace('ё', 'е').replace(')', '').replace('(', '').replace(',', '').replace('?',
                                                                                                                '').replace(
                    '!', '').replace(':', ''))
            if len(m) != 0:
                wrd = m[0]
                if wrd.tag.POS not in ('NUMR', 'PREP', 'CONJ', 'PRCL', 'INTJ', 'NPRO'):
                    f.append(wrd.normal_form)
        return f

    def input(self, msg):
        """
        Функция принимающая сообщения пользователя
        :param msg: Сообщение
        :return: Ответ пользователю, отправившему сообщение
        """

        # Проверка на команду смены мода
        self.change_attachment(None)
        # if msg.startswith("/"):
        # if msg in [mode.value for mode in Mode]:
        for mode in Mode:
            if msg in mode.value:
                self.change_keyboard(to_keyboard=open(mode.value[2], "r", encoding="UTF-8").read())
                self.change_mode(mode)
                if self.now_mode == Mode.calculationAdvertising:
                    return "Являетесь ли Вы самозанятым гражданином или фирмой*?"
                return "Вы перешли в раздел " + self.now_mode.value[1]
        # return "Неизвестный мод " + msg[1::]

        # Режим получения ответа
        if self.now_mode == Mode.get_ans:
            self.last_ans = msg
            self.now_mode = self.last_mode
            return "Ok!"

        if self.now_mode == Mode.default:
            # request_list = msg.lower().strip().replace(',', ' ').replace('.', ' ').replace('!', ' '). \
            #     replace('?', ' ').replace(':', ' ').split()
            # Правила
            if msg in Command.groupRules.value:
                try:
                    return self._vk.board.getComments(group_id=494898, topic_id=39089608, count=1)["items"][0]["text"]
                except Exception as ex:
                    config.logger.error(f'Can`t get group rules post: {ex}')
                    return None

            # Поиск специалиста на сортировке
            elif msg in Command.findSpecialist.value:
                return 'https://vk.com/@sun_sortirovka-kak-naiti-nuzhnogo-specialista-na-sortirovke'

            # Справочник полезной информации
            elif msg in Command.informationGuide.value:
                return 'https://vk.com/@sun_sortirovka-spravochnik-poleznoi-informacii'

            # Предложить новость
            elif msg in Command.offerNews.value:
                self.change_attachment('photo-187393286_457239030')
                return suggest_text()

            # Позвать админа
            elif msg in Command.callAdmin.value:
                return 'Уже зову администратора. В ближайшее время Вам ответят.'
            elif msg is not None:
                for elem in self.f_tokenizer(msg.lower()):
                    if elem in Command.offerNews_list.value:
                        if not self.user_info:
                            self.change_attachment('photo-187393286_457239030')
                            print('self.change_attachment')
                            self.user_info = True
                            return 'Здравствуйте, я бот группы Солнечная Сортировка! Если Вы хотите опубликовать' \
                                   ' новость на стене группы, то выполните следующее:\n' + suggest_text()

        if self.now_mode == Mode.advertising:

            rules = self.get_ads_rules()

            if msg in Command.advertisingRules.value:
                return rules.get('terms')
            elif msg in Command.advertisingPrice.value:
                return rules.get('price')
            elif msg in Command.advertisingProcedure.value:
                return rules.get('procedure')

        return None

    @lru_cache()
    def get_ads_rules(self) -> dict:
        rules = {}

        try:
            rules_text = self._vk_admin.board.getComments(group_id=config.group_id,
                                                          topic_id=config.advertising_conversation_id,
                                                          count=1)["items"][0]["text"]
        except Exception as ex:
            config.logger.error(f'Can`t get advertising post: {ex}')
            return rules

        blocs = rules_text.split('\n\n')
        for block in blocs:
            if block.lower().startswith('условия'):
                rules['terms'] = block
            elif block.lower().startswith('стоимость'):
                rules['price'] = block
            elif block.lower().startswith('порядок'):
                rules['procedure'] = block

        return rules


def suggest_text():
    return 'Напишите пожалуйста в предлагаемые новости на стене группы (Поле ' \
           '"Предложить новость" на главной странице. Если такого поля нет, ' \
           'убедитесь, что вы подписаны на нашу группу.)' \
           '\nДля срочной публикации воспользуйтесь функцией "Позвать администратора"'
