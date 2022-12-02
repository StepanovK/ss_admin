def cut(text: str, count: int):
    if len(text) <= count:
        return text
    elif count < 6:
        return text[:count]
    else:
        return f'{text[:count - 3]}...'
