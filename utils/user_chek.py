from Models.Users import User
from Models.Subscriptions import Subscription
from Models.Comments import Comment
from Models.Posts import Post, PostStatus
from Models.ChatMessages import ChatMessage
from Models.PrivateMessages import PrivateMessage
import datetime
import collections

degree_no_subscription = 8
degree_subscription_today = 6
degree_subscription_last_week = 5
degree_subscription_long = -7

degree_no_comments = 2
degree_one_comment = 5
degree_tho_comments = 4
degree_one_comment_with_link = 9

degree_have_some_posts = -10


def get_degree_of_user_danger(user: User):
    total_danger_degree = 0
    _add_degree_by_subscription(user, total_danger_degree)
    _add_degree_by_comments(user, total_danger_degree)
    _add_degree_by_posts(user, total_danger_degree)


def _add_degree_by_subscription(user: User, total_danger_degree: int):
    lust_subscs = Subscription.select().where(Subscription.user == user).order_by(Subscription.date.desc()).limit(1)
    if len(lust_subscs) == 0:
        total_danger_degree += degree_no_subscription
    else:
        lust_subsc = lust_subscs[0]
        if lust_subsc.date is not None:
            now = datetime.datetime.now()
            days = (now - lust_subsc.date).days
            if days <= 1:
                total_danger_degree += degree_subscription_today
            elif days <= 7:
                total_danger_degree += degree_subscription_last_week
            else:
                total_danger_degree += degree_subscription_long


def _add_degree_by_comments(user: User, total_danger_degree: int):
    last_comments = Comment.select().where(Comment.user == user).order_by(Comment.date.desc()).limit(5)
    if len(last_comments) == 0:
        total_danger_degree += degree_no_comments
    elif len(last_comments) == 1:
        comment = last_comments[0]
        if _it_is_comment_with_link(comment):
            total_danger_degree += degree_one_comment_with_link
        else:
            total_danger_degree += degree_one_comment
    elif len(last_comments) == 2:
        is_comment_with_link = False
        for comment in last_comments:
            if _it_is_comment_with_link(comment):
                is_comment_with_link = True
                break
        if is_comment_with_link:
            total_danger_degree += degree_one_comment_with_link
        else:
            total_danger_degree += degree_tho_comments


def _it_is_comment_with_link(comment: Comment) -> bool:
    words_for_check = ['http', 'www', '.ru', '.com']
    for word in words_for_check:
        if word in comment.text:
            degree = degree_one_comment_with_link
            return True
    return False


def _add_degree_by_posts(user: User, total_danger_degree: int):
    last_posted_posts = Post.select().where((Post.user == user)
                                            & (Post.suggest_status.is_null())).order_by(Post.date.desc()).limit(2)
    if len(last_posted_posts) > 0:
        total_danger_degree += degree_have_some_posts
