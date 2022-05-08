from peewee import *
from base import psql_db
from Attachments import Attachment
from Comments import Comment
from Posts import Post, PostsHashtag
from Relations import CommentsAttachment, CommentsLike, PostsAttachment, PostsLike, SuggestedPostsAttachment
from Subscriptions import Subscription
from SuggestedPosts import SuggestedPost
from Users import User


def create_all_tables():
    models = [
        User,
        Attachment,
        Post,
        PostsHashtag,
        PostsAttachment,
        PostsLike,
        Comment,
        CommentsAttachment,
        CommentsLike,
        Subscription,
        SuggestedPost,
        SuggestedPostsAttachment
    ]
    with psql_db:
        psql_db.create_tables(models)


if __name__ == '__main__':
    create_all_tables()
