from peewee import *
from Models.base import BaseModel
from Models.UploadedFiles import UploadedFile
from Models.Posts import Post
from Models.SuggestedPosts import SuggestedPost
from Models.Comments import Comment
from typing import Union


class CommentsAttachment(BaseModel):
    comment = ForeignKeyField(Comment,
                              index=True,
                              related_name='attachments',
                              backref='attachments',
                              on_delete='CASCADE')
    attachment = ForeignKeyField(UploadedFile, index=True)
    is_deleted = BooleanField()

    class Meta:
        table_name = 'comments_attachments'
        indexes = ['comment']
        order_by = ['comment']


class CommentsLike(BaseModel):
    comment = ForeignKeyField(Comment,
                              on_delete='CASCADE',
                              related_name='likes',
                              backref='likes')
    user = ForeignKeyField(Post,
                           on_delete='CASCADE',
                           related_name='liked_comments',
                           backref='liked_comments')

    class Meta:
        table_name = 'comments_likes'


class PostsAttachment(BaseModel):
    post = ForeignKeyField(Post,
                           index=True,
                           related_name='attachments',
                           backref='attachments',
                           on_delete='CASCADE')
    attachment = ForeignKeyField(UploadedFile, index=True)
    is_deleted = BooleanField()

    class Meta:
        table_name = 'posts_attachments'
        indexes = ['post']
        order_by = ['post']


class PostsLike(BaseModel):
    post = ForeignKeyField(Post,
                           on_delete='CASCADE',
                           # related_name='likes',
                           backref='likes')
    user = ForeignKeyField(Post,
                           on_delete='CASCADE',
                           # related_name='liked_posts',
                           backref='liked_posts')

    class Meta:
        table_name = 'posts_likes'


class SuggestedPostsAttachment(BaseModel):
    post = ForeignKeyField(SuggestedPost,
                           index=True,
                           related_name='attachments',
                           backref='attachments',
                           on_delete='CASCADE')
    attachment = ForeignKeyField(UploadedFile, index=True)
    is_deleted = BooleanField()

    class Meta:
        table_name = 'suggested_posts_attachments'
        indexes = ['post']
        order_by = ['post']


def add_attachment(post_or_comment: Union[Post, SuggestedPost, Comment],
                   attachment: UploadedFile,
                   is_deleted: bool = False):
    if isinstance(post_or_comment, SuggestedPost):
        new_attachment = SuggestedPostsAttachment()
        new_attachment.post = post_or_comment
    elif isinstance(post_or_comment, Post):
        new_attachment = PostsAttachment()
        new_attachment.post = post_or_comment
    elif isinstance(post_or_comment, Comment):
        new_attachment = CommentsAttachment()
        new_attachment.comment = post_or_comment
    else:
        raise 'Wrong type of object to adding a attachment!'
    new_attachment.attachment = attachment
    new_attachment.is_deleted = is_deleted
    new_attachment.save()
