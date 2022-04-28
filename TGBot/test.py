# def send_post(post: Post):
#     count_of_media = len(post.photo) + len(post.video)
#
#     images = [(lambda f: telebot.types.InputMediaPhoto(open(f, 'rb')))(f) for f in post.photo]
#     video = [(lambda f: telebot.types.InputMediaVideo(open(f, 'rb')))(f) for f in post.video]
#
#     media = []
#     media.extend(images)
#     media.extend(video)
#
#     user_name = post.user_info.get('name')
#     user_url = post.user_info.get('url')
#     mes_text = f'Новый пост от пользователя <a href="{user_url}">{user_name}</a>:\n{post.text}'
#
#     media_messages = []
#
#     if len(media) > 1:
#         media_message = t_bot.send_media_group(
#             chat_id=telegram_chat_id,
#             media=media,
#             disable_notification=True
#         )
#         media_messages.append(media_message)
#     else:
#         if len(images) == 1:
#             media_message = t_bot.send_photo(
#                 chat_id=telegram_chat_id,
#                 photo=images[0]
#             )
#             media_messages.append(media_message)
#             # media.remove(images[0])
#         if len(video) == 1:
#             media_message = t_bot.send_video(
#                 chat_id=telegram_chat_id,
#                 video=video[0]
#             )
#             media_messages.append(media_message)
#             # media.remove(video[0])
#
#     text_message = t_bot.send_message(
#         chat_id=telegram_chat_id,
#         text=mes_text
#     )
#
#     return text_message, media_messages
