from Models.Posts import Post, PostStatus
from Models.Users import User
from Models.Comments import Comment
from Models.ConversationMessages import ConversationMessage
from Models.ChatMessages import ChatMessage


def users_posts(user: User, published: bool = True):
    if published:
        return Post.select().where((Post.user == user) & (Post.suggest_status.is_null(True))).order_by(Post.date)
    else:
        return Post.select().where(
            (Post.user == user)
            & ((Post.suggest_status == PostStatus.SUGGESTED.value)
               | (Post.suggest_status == PostStatus.REJECTED.value))
        ).order_by(Post.date)


def users_comments(user: User):
    return Comment.select().where(Comment.user == user).order_by(Comment.date)


def comments_by_pages(user: User, count=6):
    comments = users_comments(user)
    pages = sort_items_by_pages(items=comments, count_per_page=count)
    return pages


def users_conv_messages(user: User):
    return ConversationMessage.select().where(ConversationMessage.user == user).order_by(ConversationMessage.date)


def conv_messages_by_pages(user: User, count=6):
    messages = users_conv_messages(user=user)
    pages = sort_items_by_pages(items=messages, count_per_page=count)
    return pages


def users_chat_messages(user: User):
    return ChatMessage.select().where(ChatMessage.user == user).order_by(ChatMessage.date)


def chat_messages_by_pages(user: User, count=6):
    messages = users_chat_messages(user=user)
    pages = sort_items_by_pages(items=messages, count_per_page=count)
    return pages


def sort_items_by_pages(items, count_per_page=6):
    pages = []
    current_page = []
    for item in items:
        current_page.append(item)
        if len(current_page) >= count_per_page:
            pages.append(current_page)
            current_page = []
    if len(current_page) > 0:
        pages.append(current_page)

    return pages
