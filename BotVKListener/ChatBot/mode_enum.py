from enum import Enum
import config


class Mode(Enum):
    default = ["Обычный режим", "default", config.chat_bot_keyboard_path + "keyboard.json", "« Назад"]
    advertising = ["advertising", "Реклама", config.chat_bot_keyboard_path + "advertising.json"]
    calculationAdvertising = ["calculation advertising", "Рассчитать стоимость", config.chat_bot_keyboard_path + "individual_or_company.json"]
    # back = ["back", "« Назад", config.chat_bot_keyboard_path + "keyboard.json"]
    get_ans = ["Режим ввода ответа"]

