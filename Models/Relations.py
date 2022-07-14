from peewee import *
from Models.base import BaseModel
from Models.UploadedFiles import UploadedFile
from Models.Posts import Post
from Models.Users import User
from Models.Comments import Comment
from Models.ConversationsMessages import ConversationsMessage
from Models.PrivateMessages import PrivateMessage
from Models.ChatMessages import ChatMessage
from typing import Union


class CommentsAttachment(BaseModel):
    comment = ForeignKeyField(Comment,
                              index=True,
                              backref='attachments',
                              on_delete='CASCADE')
    attachment = ForeignKeyField(UploadedFile, index=True)
    is_deleted = BooleanField(default=False)

    class Meta:
        table_name = 'comments_attachments'
        indexes = ['comment']
        order_by = ['comment']


class CommentsLike(BaseModel):
    liked_object = ForeignKeyField(Comment,
                                   on_delete='CASCADE',
                                   backref='likes')
    user = ForeignKeyField(User,
                           on_delete='CASCADE',
                           backref='liked_comments')

    class Meta:
        table_name = 'comments_likes'


class PostsAttachment(BaseModel):
    post = ForeignKeyField(Post,
                           index=True,
                           backref='attachments',
                           on_delete='CASCADE')
    attachment = ForeignKeyField(UploadedFile, index=True)
    is_deleted = BooleanField(default=False)

    class Meta:
        table_name = 'posts_attachments'
        indexes = ['post']
        order_by = ['post']


class PostsLike(BaseModel):
    liked_object = ForeignKeyField(Post,
                                   on_delete='CASCADE',
                                   backref='likes')
    user = ForeignKeyField(User,
                           on_delete='CASCADE',
                           backref='liked_posts')

    class Meta:
        table_name = 'posts_likes'


class PrivateMessageAttachment(BaseModel):
    message = ForeignKeyField(PrivateMessage,
                              index=True,
                              backref='attachments',
                              on_delete='CASCADE')
    attachment = ForeignKeyField(UploadedFile, index=True)
    is_deleted = BooleanField(default=False)

    class Meta:
        table_name = 'private_messages_attachments'
        indexes = ['message']
        order_by = ['message']


class ChatMessageAttachment(BaseModel):
    message = ForeignKeyField(ChatMessage,
                              index=True,
                              backref='attachments',
                              on_delete='CASCADE')
    attachment = ForeignKeyField(UploadedFile, index=True)
    is_deleted = BooleanField(default=False)

    class Meta:
        table_name = 'chat_messages_attachments'
        indexes = ['message']
        order_by = ['message']


class ConversationsMessageAttachment(BaseModel):
    message = ForeignKeyField(ConversationsMessage,
                              index=True,
                              backref='attachments',
                              on_delete='CASCADE')
    attachment = ForeignKeyField(UploadedFile, index=True)
    is_deleted = BooleanField(default=False)

    class Meta:
        table_name = 'conv_messages_attachments'
        indexes = ['message']
        order_by = ['message']


def add_attachment(attachment_object: Union[Post, Comment, PrivateMessage, ConversationsMessage, ChatMessage],
                   attachment: UploadedFile,
                   is_deleted: bool = False):
    if isinstance(attachment_object, Post):
        new_attachment, _ = PostsAttachment.get_or_create(post=attachment_object,
                                                          attachment=attachment)
    elif isinstance(attachment_object, Comment):
        new_attachment, _ = CommentsAttachment.get_or_create(comment=attachment_object,
                                                             attachment=attachment)
    elif isinstance(attachment_object, PrivateMessage):
        new_attachment, _ = PrivateMessageAttachment.get_or_create(message=attachment_object,
                                                                   attachment=attachment)
    elif isinstance(attachment_object, ConversationsMessage):
        new_attachment, _ = ConversationsMessageAttachment.get_or_create(message=attachment_object,
                                                                         attachment=attachment)
    elif isinstance(attachment_object, ChatMessage):
        new_attachment, _ = ChatMessageAttachment.get_or_create(message=attachment_object,
                                                                attachment=attachment)
    else:
        raise 'Wrong type of object to adding a attachment!'
    new_attachment.is_deleted = is_deleted
    new_attachment.save()


def add_like(post_or_comment: Union[Post, Comment], user):
    if isinstance(post_or_comment, Post):
        new_like_cls = PostsLike
    elif isinstance(post_or_comment, Comment):
        new_like_cls = CommentsLike
    else:
        raise 'Wrong type of object to adding a likes!'
    new_like = new_like_cls.get_or_create(liked_object=post_or_comment, user=user)
    return new_like


def remove_like(post_or_comment: Union[Post, Comment], user):
    if isinstance(post_or_comment, Post):
        like_cls = PostsLike
    elif isinstance(post_or_comment, Comment):
        like_cls = CommentsLike
    else:
        raise 'Wrong type of object to adding a likes!'
    try:
        like = like_cls.get(liked_object=post_or_comment, user=user)
        like.delete_instance()
    except like_cls.DoesNotExist:
        pass
