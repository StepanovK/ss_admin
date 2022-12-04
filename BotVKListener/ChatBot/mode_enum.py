from enum import Enum
import config
import os

dir_name = os.path.dirname(os.path.abspath(__file__))
keyboard_path = os.path.join(dir_name, 'keyboards/keyboard.json')
advertising_keyboard_path = os.path.join(dir_name, 'keyboards/advertising.json')
individual_or_company_keyboard_path = os.path.join(dir_name, 'keyboards/individual_or_company.json')


class Mode(Enum):
    default = ["Обычный режим", "default", keyboard_path, "« Назад"]
    advertising = ["advertising", "Реклама", advertising_keyboard_path]
    calculationAdvertising = ["calculation advertising", "Рассчитать стоимость", individual_or_company_keyboard_path]
    # back = ["back", "« Назад", config.chat_bot_keyboard_path + "keyboard.json"]
    get_ans = ["Режим ввода ответа"]
