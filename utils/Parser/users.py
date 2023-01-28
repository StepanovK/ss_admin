import datetime
from Models.Users import User
from config import logger


def add_user_by_info(vk_connection, user_info):
    user, created = User.get_or_create(id=user_info['id'])
    if created:
        update_user_info_from_vk(user, user_info['id'], vk_connection, user_info)
        user.save()
    return user


def get_or_create_user(vk_id: int, vk_connection=None):
    try:
        user = User.get_by_id(vk_id)
    except User.DoesNotExist:
        user = User.create(id=vk_id)
        if vk_connection is not None:
            update_user_info_from_vk(user, vk_id, vk_connection)
            user.save()

    return user


def vk_get_user_info(user_id: int, vk_connection, loaded_info: dict = None):
    user_info = {
        'id': user_id,
        'first_name': '',
        'last_name': '',
        'photo_max': '',
        'last_seen': '',
        'birth_date': None,
        'city': '',
        'can_write_private_message': False,
        'sex': '',
        'user_info_was_found': False
    }
    fields = 'id, first_name,last_name, photo_max, last_seen, domain, ' \
             'city, can_write_private_message, online, sex, bdate, ' \
             'photo_max_orig, photo_50'
    try:
        if loaded_info is None:
            response = vk_connection.users.get(user_ids=user_id, fields=fields)
            if isinstance(response, list) and len(response) > 0:
                loaded_info = response[0]

        if loaded_info is not None:
            user_info.update(loaded_info)
            city = user_info['city']
            user_info['city'] = city.get('title', '') if isinstance(city, dict) else str(city)
            sex = user_info.get('sex', 0)
            user_info['sex'] = 'female' if sex == 1 else 'male' if sex == 2 else ''
            user_info['can_write_private_message'] = bool(user_info.get('can_write_private_message', 0))
            user_info['user_info_was_found'] = True
            if 'bdate' in user_info:
                time_parts = str(user_info.get('bdate', '')).split('.')
                if len(time_parts) == 3:
                    user_info['birth_date'] = datetime.date(int(time_parts[2]), int(time_parts[1]),
                                                            int(time_parts[0]))
                elif len(time_parts) == 2:
                    user_info['birth_date'] = datetime.date(1904, int(time_parts[1]), int(time_parts[0]))

    except Exception as ex:
        logger.error(f"Error getting user information id{user_id}: {ex}")
    return user_info


def update_user_info_from_vk(user: User, vk_id: int, vk_connection, loaded_info: dict = None):
    user_info = vk_get_user_info(vk_id, vk_connection, loaded_info)
    if user_info.get('user_info_was_found', False):
        user.first_name = user_info.get('first_name', '')[:100]
        user.last_name = user_info.get('last_name', '')[:100]
        user.city = user_info.get('city', '')[:100]
        user.birth_date = user_info.get('birth_date')
        user.sex = user_info.get('sex', '')
        user.is_active = user_info.get('deactivated') is None
        user.domain = user_info.get('domain', '')[:100]


def users_fields():
    return 'bdate, can_post, can_see_all_posts, can_see_audio, can_write_private_message, ' \
           'city, common_count, connections, contacts, country, domain, education, has_mobile, ' \
           'last_seen, lists, online, online_mobile, photo_100, photo_200, photo_200_orig, ' \
           'photo_400_orig, photo_50, photo_max, photo_max_orig, relation, relatives, schools, ' \
           'sex, site, status, universities'
