import datetime
from peewee import fn
from Models.Admins import Admin
from Models.BanedUsers import BanedUser
from Models.Comments import Comment
from Models.Relations import CommentsLike
from Models.Relations import PostsLike
from Models.Subscriptions import Subscription
from Models.Users import User
from Models.Posts import Post, PostStatus


def main():
    now = datetime.datetime.now()
    date_from = datetime.datetime(year=now.year, month=1, day=1)
    q = Post.select(Post, fn.COUNT(PostsLike.id).alias('count_likes')).where(
        (Post.date >= date_from) & (Post.suggest_status.is_null())
    ).join(PostsLike).group_by(Post).order_by(fn.COUNT(PostsLike.id).desc()).limit(5).execute()
    print('Топ лайкнутных постов:')
    for post in q:
        print(f'{post} {post.count_likes}')

    q = Comment.select(Comment, fn.COUNT(CommentsLike.id).alias('count_likes')).where(
        (Comment.date >= date_from)
    ).join(CommentsLike).group_by(Comment).order_by(fn.COUNT(CommentsLike.id).desc()).limit(5).execute()
    print('Топ лайкнутных комментов:')
    for comment in q:
        print(f'{comment.get_url()} {comment.count_likes}')

    q = Comment.select(Comment.user, fn.COUNT(Comment.id).alias('count_comments')).where(
        (Comment.date >= date_from)
    ).group_by(Comment.user).order_by(fn.COUNT(Comment.id).desc()).limit(5).execute()
    print('Топ активных комментаторов:')
    for comment in q:
        print(f'{comment.user} {comment.count_comments}')


if __name__ == '__main__':
    main()
