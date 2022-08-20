# Бот для управления сообществом в ВК


## Основные возможности

- Получение уведомлений о новых предложенных постах
- Интерактивная обработка пердложенных постов:
  - автоподбор наиболее подходящего по тексту хэштега из списка доступных
  - ручное добавление хэштегов из списка доступных
  - просмотр короткой информации об деятельности пользователя в группе (дата подписки, последние посты, сообщения в ЛС группы...)
  - автосокрытие подписи в посте (анонимные посты)
  - публикация, или отклонение предложенной новости
- Получение информации о деятельности участников группы:
  - Дата подписки
  - Опубликованные новости
  - Отклоненные новости
  - Комментарии
  - Лайки к постам и другим комментариям
- Оповещение о подозрительных комментариях (если в группу заходят боты)
- Чат-бот в личных сообщениях группы
- Репост новых записей в телеграм (использован https://github.com/qwertyadrian/TG_AutoPoster)


### Примеры работы с оповещениями

<details><summary>Добавление хэштегов для новых постов</summary>

![new_post](https://user-images.githubusercontent.com/13664126/171338659-3c7264ed-41cc-469b-abee-52869ce60e29.gif)

</details>

<details><summary>Просмотр информации об активности пользователя</summary>

![user_info](https://user-images.githubusercontent.com/13664126/171338666-6bfe1ca7-b8b2-4461-9518-56e32619150b.gif)

</details>

<details><summary>Уведомления об опасных комментариях</summary>

![image](https://user-images.githubusercontent.com/13664126/185634328-13d4365a-f915-437d-8d2d-73e028893944.png)

![image](https://user-images.githubusercontent.com/13664126/185744595-7724648d-4dc3-4c9f-9ed0-6d70eedb4e4c.png)

![image](https://user-images.githubusercontent.com/13664126/185634492-35070266-37a4-4d5d-88df-91455b0354a9.png)

</details>

## Устройство бота

Бот состоит из двух микросервисов BotVKListener и BotVKPoster. Между собой они общаются через RabbitMQ
- BotVKListener постоянно слушает новые события, парсит их, записывает в БД и кидает уведомление
- BotVKPoster служит для работы с админами. При появлении нового поста он кидает сообщение с его описанием и кнопками с доступными действиями в специальный чат и обрабатывает действия админов.
 

# Команды для управления


## Команды в чате предложки

Команды отправляются админом в тот же чат, куда бот постит уведомления о новых постах

- `unlock_db` - разблокировать базу данных от случайного пересоздания
- `lock_db` - заблокировать базу данных от случайного пересоздания
- `recreate_db` - пересоздать базу данных (если БД уже создана, она удаляется и создаётся новая!; после создания база блокируется)
- `load_data` - загружает все данные из группы. Можно указать ID группы для загрузки данных из другой группы (`load_data 123123`)


## Команды в ЛС группы

Команды отправляются админом в личные сообщения группы

- `disable_keyboard 123123` - отключить клавиатуру. 123123 - ID чата, куда от имени группы отправляется сообщение с текстом "Клавиатура отключена" и пустой клавиатурой.
- Для принудительного обновления данных поста в БД нужно отправить в чат ссылку на пост (например: `https://vk.com/wall-123123123_1640`). В ответ бот должен прислать уведомление, что пост обновлен.
- Для получения информации о пользователе нужно отправить его ID или ссылку на профиль (например: `https://vk.com/id123321`, или `123321`). В ответ бот пришлёт сообщение с навигацией по истории деятельности пользователя в группе.


# Настройка


## Запуск ботов


Для работы ботов требуется RabbitMQ и PostgresSQL

Исполняемые файлы:
- `BotVKListener/server.py`
- `BotVKPoster/server.py`

Также можно запустить сервисы через docker-compose, используя файл конфигурации `docker-compose.yaml` из корня проекта


## Настройка переменных окружения

Для настройки требуется создать файл `.env` в корне проекта. Для этого можно скопировать и переименовать файл `.env_example`

<details><summary>Описание переменных</summary>

Настройки группы:
- `group_id` - ИД группы (без минуса)
- `group_token` - токен для управления группой
- `chat_for_suggest` - чат группы, куда будут отправляться уведомления о новых постах. Нумерация чатов начинается с 2000000000. Не забудьте отключить общую видимость чата для обычных участников.
- `chat_for_alarm` - чат группы, куда будут отправляться уведомления о вызовах адсинистратора пользователем.
- `chat_for_comments_check` - чат группы, куда будут отправляться уведомления о подозрительных комментариях
- `domain` - домен группы, если он задан
- `hashtags` - список хэштегов группы (не используется, теперь хэштеги хранятся в гугл-таблице для удобства редактирования списка)
- `admin_token` - токен админа, от имени которого будут публиковаться новости
- `admin_phone` - телефон админа (для аутентификации без токена)
- `admin_pass` - пароль админа (для аутентификации без токена)

Настройки гугл таблицы с хэштегами:
- `secret_google` - ключ доступа к гугл таблице, где на листе "Хэштэги" в первой колонке указаны все хэштеги
- `spreadsheetId` - ID документа

Настройки телеграмма:
- `api_id`, `api_hash`, `bot_token`, `channel` - описание здесь https://github.com/qwertyadrian/TG_AutoPoster

Настройки postgres:
- `POSTGRES_USER` - имя пользователя
- `POSTGRES_PASSWORD` - пароль
- `PGADMIN_DEFAULT_EMAIL` - логин для настройки PG-Admin
- `PGADMIN_DEFAULT_PASSWORD` - пароль для настройки PG-Admin
- `PGADMIN_CONFIG_SERVER_MODE=False` - всегда

</details>
