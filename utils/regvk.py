import re
from datetime import datetime

import requests


def parse_russian_date(date_str):
    """
    Парсит русскую дату в формате '14 июня 2007 года'
    """
    try:
        # Убираем слово "года" и лишние пробелы
        date_str_clean = date_str.replace('года', '').strip()

        # Словарь для замены русских названий месяцев
        month_mapping = {
            'января': '01',
            'февраля': '02',
            'марта': '03',
            'апреля': '04',
            'мая': '05',
            'июня': '06',
            'июля': '07',
            'августа': '08',
            'сентября': '09',
            'октября': '10',
            'ноября': '11',
            'декабря': '12'
        }

        # Разбиваем дату на части
        parts = date_str_clean.split()
        if len(parts) >= 3:
            day = parts[0].zfill(2)  # День
            month_ru = parts[1]  # Месяц на русском
            year = parts[2]  # Год

            # Заменяем русский месяц на числовой
            if month_ru in month_mapping:
                month = month_mapping[month_ru]

                # Собираем дату в формате DD.MM.YYYY
                formatted_date = f"{day}.{month}.{year}"

                # Парсим в datetime
                return datetime.strptime(formatted_date, '%d.%m.%Y')
            else:
                print(f"Неизвестный месяц: {month_ru}")
                return None
        else:
            print(f"Неверный формат даты: {date_str}")
            return None

    except Exception as e:
        print(f"Ошибка парсинга даты '{date_str}': {e}")
        return None


def get_registration_date(vk_id):
    url = "https://regvk.com/"

    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'content-type': 'application/x-www-form-urlencoded',
    }

    data = {'link': str(vk_id), 'button': 'Определить дату регистрации'}

    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)

        # Ищем паттерн даты
        match = re.search(r'Дата регистрации:\s*(\d+\s+\w+\s+\d+)\s*года', response.text)
        if match:
            date_str = match.group(1)
            return parse_russian_date(date_str)

        return None

    except Exception as e:
        print(f"Ошибка: {e}")
        return None


# Пример использования
if __name__ == "__main__":
    test_vk_id = 700001

    date = get_registration_date(test_vk_id)
    if date:
        print(f"Дата регистрации: {date.strftime('%d.%m.%Y')}")
