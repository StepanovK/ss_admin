from vk_api.keyboard import VkKeyboard, VkKeyboardButton, VkKeyboardColor
from Models.Posts import Post, PostStatus


def main_menu_keyboard(post: Post):
    keyboard = VkKeyboard(one_time=False, inline=True)

    if post.suggest_status == PostStatus.SUGGESTED.value:
        keyboard.add_callback_button(label='Опубликовать',
                                     color=VkKeyboardColor.PRIMARY,
                                     payload={"command": "public_post", "post_id": post.id})
        keyboard.add_line()
        keyboard.add_callback_button(label='Добавить хэштеги',
                                     color=VkKeyboardColor.SECONDARY,
                                     payload={"command": "add_hashtags", "post_id": post.id})
        keyboard.add_line()

    keyboard.add_callback_button(label='Информация о пользователе',
                                 color=VkKeyboardColor.SECONDARY,
                                 payload={"command": "show_user_info", "post_id": post.id})

    if post.suggest_status == PostStatus.SUGGESTED.value:
        keyboard.add_line()
        keyboard.add_callback_button(label='Отклонить',
                                     color=VkKeyboardColor.NEGATIVE,
                                     payload={"command": "reject", "post_id": post.id})

    return keyboard.get_keyboard()
