from BotVK.server import Server
from BotVK import config

import datetime

from BotVK.Parser import subscriptions
from BotVK.Parser import posts
from BotVK.Parser import users
from BotVK.config import logger
from Models.Users import User

temp_file_name = 'current_offset_of_posts.tmp'


def load_all(vk_connection, group_id):
    logger.info('Загрузка подписчиков начата')
    load_subscribers(vk_connection, group_id)
    logger.info('Загрузка подписчиков завершена')

    logger.info('Загрузка постов начата')
    load_posts(vk_connection, group_id)
    logger.info('Загрузка постов завершена')


def load_subscribers(vk_connection, group_id):
    users_fields = 'bdate, can_post, can_see_all_posts, can_see_audio, can_write_private_message, ' \
                   'city, common_count, connections, contacts, country, domain, education, has_mobile, ' \
                   'last_seen, lists, online, online_mobile, photo_100, photo_200, photo_200_orig, ' \
                   'photo_400_orig, photo_50, photo_max, photo_max_orig, relation, relatives, schools, ' \
                   'sex, site, status, universities'
    subs = vk_connection.groups.getMembers(group_id=group_id, sort='time_asc', fields=users_fields)
    for user_info in subs['items']:
        user = User.create(id=user_info['id'])
        users.update_user_info_from_vk(user, user_info['id'], vk_connection, user_info)
        user.save()

        subscriptions.add_subscription(group_id=group_id,
                                       user_id=user_info['id'],
                                       vk_connection=vk_connection,
                                       is_subscribed=True,
                                       subs_date=datetime.date(2000, 1, 1))


def load_posts(vk_connection, group_id):
    offset = get_current_offset_of_posts()
    while True:
        logger.info(f'offset={offset}')
        vk_posts = vk_connection.wall.get(owner_id=-group_id, offset=offset, count=100)['items']
        if len(vk_posts) == 0:
            break
        for vk_post in vk_posts:
            likers = vk_connection.wall.getLikes(owner_id=-group_id, post_id=vk_post['id'], count=1000)
            vk_post['likers'] = likers.get('users', [])
            found_post = posts.parse_wall_post(vk_post)


        offset += 100
        update_current_offset_of_posts(offset)



def update_current_offset_of_posts(offset):
    with open(temp_file_name, 'w') as tmp_file:
        tmp_file.write(str(offset))
        tmp_file.close()


def get_current_offset_of_posts():
    offset = 0
    try:
        with open(temp_file_name, 'r') as tmp_file:
            str_offset = tmp_file.read()
            offset = 0 if str_offset == '' else int(str_offset)
            tmp_file.close()
    except FileNotFoundError:
        pass
    return offset


if __name__ == '__main__':
    server = Server(vk_group_token=config.group_token,
                    admin_token=config.admin_token,
                    admin_phone=config.admin_phone,
                    admin_pass=config.admin_pass,
                    vk_group_id=config.group_id)
    load_all(server.vk_connection_admin, config.group_id)
