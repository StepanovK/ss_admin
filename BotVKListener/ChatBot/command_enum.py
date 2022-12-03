from enum import Enum


class Command(Enum):
    """ groupRules """
    groupRules = ["group rules", "Правила группы"]

    """ findSpecialist """
    findSpecialist = ["find specialist", "Поиск специалистов"]

    """ informationGuide """
    informationGuide = ["information guide", "Справочник полезной информации"]

    """ advertising """
    advertising = ["advertising", "Реклама"]

    """ advertisingRules """
    advertisingRules = ["advertising rules", "Правила рекламы"]

    """ advertisingPrice """
    advertisingPrice = ["advertising price", "Стоимость рекламы"]

    """ advertisingProcedure """
    advertisingProcedure = ["advertising procedure", "Порядок размещения рекламы"]

    """ offerNews """
    offerNews = ["offer news", "Предложить новость"]

    """ calculationAdvertising """
    calculationAdvertising = ["calculation advertising", "Рассчитать стоимость"]

    callAdmin = ["call administration", "Позвать администратора"]

    """ individual_or_company """
    individual = ["individual", "Самозанятый"]
    company = ["company", "Фирма"]
    offerNews_list = ['найти', 'подсказать', 'пропасть', 'утерять', 'потерять', 'разместить', 'вопрос', 'опубликовать',
                      'предложить', 'спросить', 'знать', 'выложить', 'узнать']