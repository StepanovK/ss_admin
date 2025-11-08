import datetime

from Models.ChatMessages import ChatMessage
from Models.Comments import Comment
from Models.Posts import Post
from Models.Subscriptions import Subscription
from Models.Users import User

_degree_no_subscription = 8
_degree_subscription_today = 6
_degree_subscription_last_week = 5
_degree_subscription_long = -7

_degree_no_comments = 2
_degree_one_comment = 5
_degree_tho_comments = 4
_degree_one_comment_with_link = 9

_degree_have_some_posts = -10

_degree_reg_date_last_week = 3
_degree_reg_date_last_month = 2
_degree_reg_date_last_year = 1


def get_degree_of_user_danger(user: User):
    total_danger_degree = 0
    total_danger_degree += _get_degree_by_subscription(user)
    total_danger_degree += _get_degree_by_comments(user)
    total_danger_degree += _get_degree_by_posts(user)
    total_danger_degree += get_degree_by_reg_date(user)
    return total_danger_degree


def _get_degree_by_subscription(user: User):
    degree = 0
    lust_subscs = Subscription.select().where(Subscription.user == user).order_by(Subscription.date.desc()).limit(1)
    if len(lust_subscs) == 0:
        degree += _degree_no_subscription
    else:
        lust_subsc = lust_subscs[0]
        if lust_subsc.date is not None:
            now = datetime.datetime.now()
            days = (now - lust_subsc.date).days
            if days <= 1:
                degree += _degree_subscription_today
            elif days <= 7:
                degree += _degree_subscription_last_week
            else:
                degree += _degree_subscription_long
    return degree


def _get_degree_by_comments(user: User):
    degree = 0
    last_comments = Comment.select().where(Comment.user == user).order_by(Comment.date.desc()).limit(3)
    last_chat_messages = ChatMessage.select().where(ChatMessage.user == user).order_by(ChatMessage.date.desc()).limit(3)
    if len(last_comments) + len(last_chat_messages) == 0:
        degree += _degree_no_comments
    elif len(last_comments) == 1 and len(last_chat_messages) == 0:
        comment = last_comments[0]
        if _it_is_text_with_link(comment.text):
            degree += _degree_one_comment_with_link
        else:
            degree += _degree_one_comment
    elif len(last_chat_messages) == 1 and len(last_comments) == 0:
        last_chat_message = last_chat_messages[0]
        if _it_is_text_with_link(last_chat_message.text):
            degree += _degree_one_comment_with_link
        else:
            degree += _degree_one_comment
    elif len(last_comments) + len(last_chat_messages) <= 2:
        is_comment_with_link = False
        for comment in last_comments:
            if _it_is_text_with_link(comment.text):
                is_comment_with_link = True
                break
        for message in last_chat_messages:
            if _it_is_text_with_link(message.text):
                is_comment_with_link = True
                break
        if is_comment_with_link:
            degree += _degree_one_comment_with_link
        else:
            degree += _degree_tho_comments
    return degree


def _it_is_text_with_link(text_for_check: str):
    words_for_check = ['http', 'www', '.ru', '.com', '.me/', '.ly/']
    for word in words_for_check:
        if word in text_for_check:
            return True
    return False


def _get_degree_by_posts(user: User):
    degree = 0
    last_posted_posts = Post.select().where((Post.user == user)
                                            & (Post.suggest_status.is_null())).order_by(Post.date.desc()).limit(2)
    if len(last_posted_posts) > 0:
        degree += _degree_have_some_posts
    return degree


def get_degree_by_reg_date(user: User):
    degree = 0
    if user.registration_date is not None:
        if isinstance(user.registration_date, datetime.datetime):
            delta = (datetime.date.today() - user.registration_date.date())
        else:
            delta = (datetime.date.today() - user.registration_date)

        if delta.days <= 7:  # Аккаунт создан меньше недели назад
            degree = _degree_reg_date_last_week
        if delta.days <= 31:  # Аккаунт создан меньше месяца назад
            degree = _degree_reg_date_last_month
        elif delta.days <= (365 * 1.5):  # Аккаунт создан меньше 1,5 лет назад
            degree = _degree_reg_date_last_year
        else:
            degree = 0

    return degree
