
def format_time_difference(seconds: int) -> str:
    """
    Форматирует разницу во времени в наиболее удобном формате

    Args:
        seconds: разница в секундах

    Returns:
        str: отформатированная разница во времени
    """
    if seconds <= 60:
        return f"{seconds} сек"

    minutes, seconds = divmod(seconds, 60)
    if minutes <= 60:
        return f"{minutes} мин {seconds} сек"

    hours, minutes = divmod(minutes, 60)
    if hours <= 24:
        return f"{hours} ч {minutes} мин {seconds} сек"

    days, hours = divmod(hours, 24)
    return f"{days} дн {hours} ч {minutes} мин {seconds} сек"


def format_time_difference_pretty(seconds: int) -> str:
    """
    Форматирует разницу во времени с красивыми окончаниями
    """
    if seconds < 60:
        return f"{seconds} секунд"

    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes} {_pluralize(minutes, 'минута', 'минуты', 'минут')} " \
               f"{seconds} {_pluralize(seconds, 'секунда', 'секунды', 'секунд')}"

    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours} {_pluralize(hours, 'час', 'часа', 'часов')} " \
               f"{minutes} {_pluralize(minutes, 'минута', 'минуты', 'минут')}"

    days, hours = divmod(hours, 24)
    if days < 30:
        return f"{days} {_pluralize(days, 'день', 'дня', 'дней')} " \
               f"{hours} {_pluralize(hours, 'час', 'часа', 'часов')}"

    # Для очень больших промежутков
    months, days = divmod(days, 30)
    if months < 12:
        return f"{months} {_pluralize(months, 'месяц', 'месяца', 'месяцев')} " \
               f"{days} {_pluralize(days, 'день', 'дня', 'дней')}"

    years, months = divmod(months, 12)
    return f"{years} {_pluralize(years, 'год', 'года', 'лет')} " \
           f"{months} {_pluralize(months, 'месяц', 'месяца', 'месяцев')}"


def _pluralize(number: int, form1: str, form2: str, form5: str) -> str:
    """
    Выбирает правильную форму слова для числа
    """
    n = abs(number) % 100
    n1 = n % 10

    if 10 < n < 20:
        return form5
    if n1 == 1:
        return form1
    if 1 < n1 < 5:
        return form2
    return form5