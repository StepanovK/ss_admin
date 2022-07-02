import functools
from collections import Counter
from typing import List, Dict

from Models.Posts import Post
from config import spreadsheetId
from utils.googleSheetsManager import GoogleSheetsManager
from rapidfuzz import process, fuzz


@functools.lru_cache()
def get_hashtags(new_post: str, count_res: int = 20) -> List[tuple]:
    _google_sheet: GoogleSheetsManager = GoogleSheetsManager(spreadsheetId)
    raw_hashtags: dict = _google_sheet.get_sheet_values("Хэштэги")
    posts_with_hashtag: List[str] = [post.text.lower() for post in Post.select().where(Post.text.contains("#"))]
    ht_posts_dict: Dict[str: set] = {}
    for elem in raw_hashtags:
        hash_tag = elem.get('Hashtag')
        if hash_tag is not None:
            ht_posts_dict[hash_tag] = set()
            for post in posts_with_hashtag:
                if hash_tag.strip().lower() in post:
                    ht_posts_dict[hash_tag].add(post.replace(hash_tag.strip().lower(), ''))
    result_hashtag: Dict[str: int] = {}
    for hashtag in ht_posts_dict:
        a: list = process.extract(new_post, ht_posts_dict[hashtag], scorer=fuzz.WRatio, limit=5)
        res: int = 0
        for elem in a:

            res += elem[1]
        result_hashtag[hashtag] = res
    c = Counter(result_hashtag)
    hashtags: List[tuple] = c.most_common(count_res)
    return hashtags


if __name__ == "__main__":
    print(get_hashtags("Пропала кошечка"))