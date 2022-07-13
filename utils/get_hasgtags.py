import functools
from collections import Counter, defaultdict
from typing import List, Dict, Union

from Models.Posts import Post, PostsHashtag
from config import spreadsheetId
from utils.googleSheetsManager import GoogleSheetsManager
from rapidfuzz import process, fuzz


@functools.lru_cache()
def get_hashtags() -> List:
    _google_sheet: GoogleSheetsManager = GoogleSheetsManager(spreadsheetId)
    raw_hashtags: dict = _google_sheet.get_sheet_values("Хэштэги")
    hashtags = []
    for elem in raw_hashtags:
        hash_tag = elem.get('Hashtag')
        if hash_tag is not None and hash_tag != '':
            hashtags.append(hash_tag)
    hashtags.sort()
    return hashtags


def get_sorted_hashtags(new_post: Post, count_res: Union[int, None] = None) -> List[tuple]:
    posts_with_hashtag: List[str] = [post.text.lower() for post in Post.select().where(Post.text.contains("#"))]
    ht_posts_dict: Dict[str: set] = defaultdict(set)
    last_posts = PostsHashtag.select(Post.text, PostsHashtag.hashtag).join(Post).order_by(Post.date.desc()).limit(1000)
    for post_with_ht in last_posts:
        ht = post_with_ht.hashtag
        post_text = post_with_ht.post.text
        ht_posts_dict[ht].add(post_text.lower())
    result_hashtag: Dict[str: int] = {}
    new_post_text_l = new_post.text.lower()
    for hashtag in ht_posts_dict:
        a: list = process.extract(new_post_text_l, ht_posts_dict[hashtag], scorer=fuzz.WRatio, limit=5)
        res: int = 0
        for elem in a:
            res += elem[1]
        result_hashtag[hashtag] = res
    c = Counter(result_hashtag)
    return c.most_common(count_res)
