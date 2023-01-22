import functools
from collections import Counter, defaultdict
from typing import List, Dict, Union

from Models.Posts import Post, PostsHashtag
from config import spreadsheetId
from utils.googleSheetsManager import GoogleSheetsManager
from rapidfuzz import process, fuzz
from utils.openai_bot import ChatGPT


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
    ht_posts_dict: Dict[str: set] = defaultdict(set)
    last_posts = PostsHashtag.select(Post.text, PostsHashtag.hashtag).join(Post).where(
        (Post.suggest_status.is_null()) & (Post.is_deleted == False)).order_by(Post.date.desc())
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


def choice_hashtags_ai(mes_text: str, hashtags: list[str]) -> list[str]:
    th_text_list = [f' - {ht}' for ht in hashtags]
    ht_text = '\n'.join(th_text_list)

    question = f'Отвечай коротко. Какой хэштег из списка:\n{ht_text}\n подходит к тексту: "{mes_text}"?'
    chat = ChatGPT()
    answer = chat.get_answer(question)
    # print(answer)
    relevant_hashtags = []
    answer_low = answer.lower()
    for ht in hashtags:
        if ht.lower() in answer_low:
            relevant_hashtags.append(ht)

    return relevant_hashtags


if __name__ == '__main__':
    mes = 'Посоветуйте хорошего парикмахера на Сортировке'
    htags = choice_hashtags_ai(mes, get_hashtags())
    print(f'Для текста "{mes}" выбраны хэштеги: {htags}')

    mes = 'Чья кошка сидит в подъезде уже вторую неделю? Хозяин, отзовись!'
    htags = choice_hashtags_ai(mes, get_hashtags())
    print(f'Для текста "{mes}" выбраны хэштеги: {htags}')

    mes = 'В ООО "Рога и копыта" требуется повар и разводчик мышей. Зарплата маленькая, зато бесплатное питание.'
    htags = choice_hashtags_ai(mes, get_hashtags())
    print(f'Для текста "{mes}" выбраны хэштеги: {htags}')
