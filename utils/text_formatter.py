def format_text(source_text: str) -> str:
    new_text = replace_double_spaces(source_text)

    spaces = [' ', '\n']
    symbols = [',', '.', '!', '?', ';', ':', '-']
    for space in spaces:
        for symbol in symbols:
            new_text = new_text.replace(space + symbol, symbol + space)
    new_text = replace_double_spaces(new_text)
    new_text = new_text.replace('-', ' -')

    for symbol in symbols:
        new_text = new_text.replace(symbol, symbol + ' ')
    new_text = replace_double_spaces(new_text)

    new_text = new_text.replace(' \n', '\n')

    start_symbols = ['.', '?', '!', '\n']
    for symbol in start_symbols:
        parts = new_text.split(symbol)
        new_parts = []
        for part in parts:
            if part != '':
                count_symbols = 2 if part[0:1] == ' ' else 1
                new_part = part[0:count_symbols].title() + part[count_symbols:]
                new_parts.append(new_part)

        if symbol == '\n':
            while len(new_parts) > 0 and (
                    new_parts[-1] == ''
                    or new_parts[-1] == ' '
            ):
                new_parts = new_parts[0:-1]

        new_text = symbol.join(new_parts)

    while new_text[-1] == ' ':
        new_text = new_text[0:-1]

    return new_text


def replace_double_spaces(source_text: str) -> str:
    new_text = source_text
    while '  ' in new_text:
        new_text = new_text.replace('  ', ' ')
    return new_text


def test():
    assert format_text('Ляляля , ляляля') == 'Ляляля, ляляля'
    assert format_text('Ляляля  ,   ляляля') == 'Ляляля, ляляля'
    assert format_text('Ляляля  !   ') == 'Ляляля!'
    assert format_text('Ляляля  ?ляляля') == 'Ляляля? Ляляля'
    assert format_text('Ляляля,ляляля') == 'Ляляля, ляляля'
    assert format_text('Ляляля ,ляляля') == 'Ляляля, ляляля'
    assert format_text('Ляляля :ляляля') == 'Ляляля: ляляля'
    assert format_text('Ляляля ;ляляля') == 'Ляляля; ляляля'
    assert format_text('Ляляля . 111') == 'Ляляля. 111'
    assert format_text('Ляляля.111') == 'Ляляля. 111'
    assert format_text('Ляляля .ляляля') == 'Ляляля. Ляляля'
    assert format_text('Ляляля .ляляля') == 'Ляляля. Ляляля'
    assert format_text('ляляля .ляляля') == 'Ляляля. Ляляля'
    assert format_text('ляляля\n.ляляля') == 'Ляляля.\nЛяляля'
    assert format_text('ляляля  \nляляля') == 'Ляляля\nЛяляля'
    assert format_text('Ляляля! ') == 'Ляляля!'
    assert format_text('Ляляля!\n ') == 'Ляляля!'
    assert format_text('ляляля -ляляля') == 'Ляляля - ляляля'


if __name__ == '__main__':
    test()
