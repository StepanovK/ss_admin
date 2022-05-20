from BotVK.server import Server
from BotVK import config

import datetime

from BotVK.Parser import subscriptions
from BotVK.Parser import posts
from BotVK.Parser import users
from BotVK.Parser import comments
from BotVK.config import logger
from Models.Users import User
from Models.Posts import Post


def load_all(vk_connection, group_id):
    logger.info('Загрузка подписчиков начата')
    load_subscribers(vk_connection, group_id)
    logger.info('Загрузка подписчиков завершена')

    logger.info('Загрузка постов начата')
    load_posts(vk_connection, group_id)
    logger.info('Загрузка постов завершена')

    logger.info('Загрузка комментариев начата')
    load_comments(vk_connection, group_id)
    logger.info('Загрузка комментариев завершена')


def load_subscribers(vk_connection, group_id):
    subs = vk_connection.groups.getMembers(group_id=group_id, sort='time_asc', fields=users_fields())
    for user_info in subs['items']:
        user = add_user_by_info(vk_connection, user_info)

        subscriptions.add_subscription(group_id=group_id,
                                       user_id=user_info['id'],
                                       vk_connection=vk_connection,
                                       is_subscribed=True,
                                       subs_date=datetime.date(2000, 1, 1))


def users_fields():
    return 'bdate, can_post, can_see_all_posts, can_see_audio, can_write_private_message, ' \
           'city, common_count, connections, contacts, country, domain, education, has_mobile, ' \
           'last_seen, lists, online, online_mobile, photo_100, photo_200, photo_200_orig, ' \
           'photo_400_orig, photo_50, photo_max, photo_max_orig, relation, relatives, schools, ' \
           'sex, site, status, universities'


def load_posts(vk_connection, group_id):
    temp_file_name = 'current_offset_of_posts.tmp'

    offset = get_current_offset_in_file(temp_file_name)
    while True:
        if offset != 0:
            logger.info(f'Загрузка постов начата со смещением = {offset}')
        vk_posts = vk_connection.wall.get(owner_id=-group_id,
                                          offset=offset,
                                          count=100)['items']
        if len(vk_posts) == 0:
            break
        for vk_post in vk_posts:
            likers = vk_connection.wall.getLikes(owner_id=-group_id, post_id=vk_post['id'], count=1000)
            vk_post['likers'] = likers.get('users', [])
            post = posts.parse_wall_post(vk_post)
            print(f'Загружен пост {post}')

        offset += 100
        update_current_offset_in_file(offset, temp_file_name)


def load_comments(vk_connection, group_id):
    temp_file_name = 'current_offset_of_posts_for_comments.tmp'
    post_offset = get_current_offset_in_file(temp_file_name)
    if post_offset != 0:
        logger.info(f'Загрузка комментов начата с поста с id={post_offset}')

    count_for_get = 100  # min = 10, max = 100
    for post in Post.select().where(Post.is_deleted == False,
                                    Post.owner_id == -group_id,
                                    Post.vk_id > post_offset).order_by(Post.vk_id):
        offset = 0
        count = 0
        params = {'owner_id': -group_id,
                  'post_id': post.vk_id,
                  'need_likes': 1,
                  'count': count_for_get,
                  'sort': 'asc',
                  'extended': 1,
                  'fields': users_fields(),
                  'thread_items_count': 10}
        while True:
            vk_comments = vk_connection.wall.getComments(offset=offset, **params)
            for user_info in vk_comments['profiles']:
                user = add_user_by_info(vk_connection, user_info)
            for vk_comment in vk_comments['items']:
                comment = comments.parse_comment(vk_comment, vk_connection)
                count += 1

                thread = vk_comment.get('thread', {})
                comments_in_thread = []
                if 1 < thread.get('count', 0) < 10:
                    comments_in_thread = thread.get('items', [])
                elif thread.get('count', 0) > 10:
                    vk_comment_with_thread = vk_connection.wall.getComments(comment_id=vk_comment['id'], **params)
                    comments_in_thread = vk_comment_with_thread.get('items', [])

                for vk_comment_in_thread in comments_in_thread:
                    comment_in_thread = comments.parse_comment(vk_comment_in_thread, vk_connection)
                    count += 1

            offset += count_for_get
            if vk_comments['count'] < count_for_get:
                break

        if count > 0:
            print(f'Загружено {count} комментов {post}')
            update_current_offset_in_file(post.vk_id, temp_file_name)


def add_user_by_info(vk_connection, user_info):
    user, created = User.get_or_create(id=user_info['id'])
    if created:
        users.update_user_info_from_vk(user, user_info['id'], vk_connection, user_info)
        user.save()
    return user


def update_current_offset_in_file(offset, temp_file_name):
    with open(temp_file_name, 'w') as tmp_file:
        tmp_file.write(str(offset))
        tmp_file.close()


def get_current_offset_in_file(temp_file_name):
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
