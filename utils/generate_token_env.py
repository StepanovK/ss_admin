"""
Скрипт для генерации токена и вывода его в формате для .env
Запускается локально (не в Docker) для получения токена
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.vk_oauth import VKOAuth
import datetime


def generate_token_for_env():
    """Генерирует токен и выводит строки для добавления в .env"""
    print('=' * 60)
    print('Генерация токена администратора для .env файла')
    print('=' * 60)

    oauth = VKOAuth()

    print('\n1. Перейдите по ссылке и авторизуйтесь:')
    print(f'\n{oauth.get_auth_url()}\n')

    code = input('2. Вставьте код из адресной строки (после code=): ').strip()

    if not code:
        print('Ошибка: код не введён')
        return

    print('\n3. Получаем токен...')
    tokens = oauth.get_token_by_code(code)

    if tokens:
        expires_at = datetime.datetime.now() + datetime.timedelta(seconds=tokens['expires_in'])

        print('\n' + '=' * 60)
        print('Добавьте следующие строки в ваш .env файл:')
        print('=' * 60)
        print(f'ADMIN_ACCESS_TOKEN={tokens["access_token"]}')
        print(f'ADMIN_REFRESH_TOKEN={tokens["refresh_token"]}')
        print(f'ADMIN_TOKEN_EXPIRES_AT={expires_at.isoformat()}')
        print('=' * 60)
        print('\n⚠️ Важно: Токен действителен до:', expires_at.strftime('%Y-%m-%d %H:%M:%S'))
        print('⚠️ После истечения токена потребуется обновить его в .env файле и перезапустить бота')
    else:
        print('\n❌ Не удалось получить токен. Проверьте код и настройки OAuth.')


if __name__ == '__main__':
    generate_token_for_env()
