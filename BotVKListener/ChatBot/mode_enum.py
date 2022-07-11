from enum import Enum


class Mode(Enum):
    default = ["Обычный режим", "default", "BotVKListener/ChatBot/keyboards/keyboard.json", "« Назад"]
    advertising = ["advertising", "Реклама", "BotVKListener/ChatBot/keyboards/advertising.json"]
    calculationAdvertising = ["calculation advertising", "Рассчитать стоимость", "BotVKListener/ChatBot/keyboards/individual_or_company.json"]
    # back = ["back", "« Назад", "BotVKListener/ChatBot/keyboards/keyboard.json"]
    get_ans = ["Режим ввода ответа"]

