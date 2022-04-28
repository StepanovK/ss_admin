import psycopg2


def get_db_connection(config_bd):
    try:
        connection = psycopg2.connect(
            host=config_bd.db_host,
            port=config_bd.db_port,
            user=config_bd.db_user,
            password=config_bd.db_password,
            database=config_bd.db_name
        )
        return connection
    except Exception as ex:
        connection_info = f'host={config.db_host}, port={config.db_port},' \
                          f' user={config.db_user} password={config.db_password}'
        logger.error(f"Проблема при подключении к базе данных {config.db_name}\n({connection_info}):", ex)
        return None


class User:

    def __init__(self, id, config_db=None, db_connection=None):
        self.id = id
        self.first_name = ''
        self.last_name = ''
        self.birth_date = None
        self.subscription_date = None
        self.is_active = False
        self._config_db = config_db
        self._db_connection = db_connection

    def read(self):
        if self._config_db is None:
            conn = self._db_connection
        else:
            conn = get_db_connection(self._config_db)

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""SELECT * from users where id = %s""", [self.id])
            user_info = cursor.fetchone()
            if user_info is not None:
                self.first_name = user_info.first_name
                self.last_name = user_info.last_name
                self.birth_date = user_info.birth_date
                self.subscription_date = user_info.subscription_date
                self.is_active = user_info.is_active
            else:
                raise f'Can`t find user by id <{self.id}>'

    def write(self):
        if self._config_db is None:
            conn = self._db_connection
        else:
            conn = get_db_connection(self._config_db)

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""SELECT * from users where id = %s""", [self.id])
            user_info = cursor.fetchone()
            if user_info is not None:
                self.first_name = user_info.first_name
                self.last_name = user_info.last_name
                self.birth_date = user_info.birth_date
                self.subscription_date = user_info.subscription_date
                self.is_active = user_info.is_active
            else:
                raise f'Can`t find user by id <{self.id}>'


class Post:

    def __init__(self):
        self.post_id = None
        self.text = ''
        self.photo = []
        self.video = []
        # self.docs = []
        self.user_id = None
        self.user_info = None
        self.date = None
        self.post_type = None
        self.owner_id = None
        self.link = ''

    def pars_wall_post(self, wall_post):
        if wall_post.type == VkBotEventType.WALL_POST_NEW:
            self.text = wall_post.object['text']
            self.user_id = wall_post.object['from_id']
            self.user_info = get_user_info(self.user_id)
            self.date = wall_post.object['date']
            self.post_type = wall_post.object['post_type']
            self.post_id = wall_post.object['id']
            self.owner_id = wall_post.object['owner_id']
            if self.owner_id is not None and self.post_id is not None:
                self.link = f'{vk_link}wall{self.owner_id}_{self.post_id}'
            for attachment in wall_post.object.get('attachments', []):
                attachment_type = attachment.get('type')
                if attachment_type == 'photo':
                    sizes = attachment.get('photo', {}).get('sizes', [])
                    if len(sizes) > 0:
                        max_size = sizes[-1]
                        try:
                            photo = download(max_size['url'], out=cache_dir)
                            photo = photo.replace('/', '\\')
                        except Exception as _ex:
                            photo = None
                            logger.error(f'Ошибка при загрузки фото: \n{attachment} \n{_ex}')
                        if photo:
                            self.photo.append(photo)
                            # with open(photo, 'rb') as photo_file:
                            #     self.photo.append(photo_file)
                            # os.remove(photo)

        # @logger.catch()


def get_user_info(user_id):
    user_info = {
        'id': user_id,
        'url': f'{vk_link}id{user_id}',
        'name': '',
        'first_name': '',
        'last_name': '',
        'photo_max': '',
        'last_seen': '',
        'city': '',
        'can_write_private_message': False,
        'online': False,
        'sex': '',
        'chat_name': f'[id{user_id}]',
        'user_info_is_found': False
    }
    try:
        fields = 'id, first_name,last_name, photo_max, last_seen, city, can_write_private_message, online, sex'
        response = vk.users.get(user_ids=user_id, fields=fields)
        if isinstance(response, list) and len(response) > 0:
            user_info.update(response[0])
            city = user_info['city']
            user_info['city'] = city.get('title', '') if isinstance(city, dict) else city
            sex = user_info.get('sex', 0)
            user_info['sex'] = 'female' if sex == 1 else 'male' if sex == 2 else ''
            user_info['name'] = '{} {}'.format(user_info.get('last_name', ''), user_info.get('first_name', ''))
            user_info['chat_name'] = '[id{}|{}]'.format(user_id, user_info.get('name', ''))
            user_info['online'] = bool(user_info.get('online', 0))
            user_info['can_write_private_message'] = bool(user_info.get('can_write_private_message', 0))
            user_info['user_info_is_found'] = True
    except Exception as _ex:
        print("Ошибка получения информации о пользователе: {0}".format(_ex))
    return user_info


# @logger.catch()
def send_post(post: Post):
    count_of_media = len(post.photo) + len(post.video)

    images = [(lambda f: telebot.types.InputMediaPhoto(open(f, 'rb')))(f) for f in post.photo]
    video = [(lambda f: telebot.types.InputMediaVideo(open(f, 'rb')))(f) for f in post.video]

    media = []
    media.extend(images)
    media.extend(video)

    user_name = post.user_info.get('name')
    user_url = post.user_info.get('url')
    mes_text = f'Новый пост от пользователя <a href="{user_url}">{user_name}</a>:\n{post.text}'

    media_messages = []

    if len(media) > 1:
        media_message = t_bot.send_media_group(
            chat_id=telegram_chat_id,
            media=media,
            disable_notification=True
        )
        media_messages.append(media_message)
    else:
        if len(images) == 1:
            media_message = t_bot.send_photo(
                chat_id=telegram_chat_id,
                photo=images[0]
            )
            media_messages.append(media_message)
            # media.remove(images[0])
        if len(video) == 1:
            media_message = t_bot.send_video(
                chat_id=telegram_chat_id,
                video=video[0]
            )
            media_messages.append(media_message)
            # media.remove(video[0])

    text_message = t_bot.send_message(
        chat_id=telegram_chat_id,
        text=mes_text
    )

    return text_message, media_messages


try:
    for event in longpoll.listen():

        if event.type == VkBotEventType.WALL_POST_NEW:
            new_post = Post()
            new_post.pars_wall_post(event)
            send_post(new_post)

except Exception as ex:
    logger.error(ex)
