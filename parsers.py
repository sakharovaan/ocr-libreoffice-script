import re
import logging
import nltk
import string

MIDDLE_DASH_BETWEEN_DIGITS_REGEXP = re.compile(r'(\d+)\s*[-—–]\s*(\d+)', re.MULTILINE)


def middle_dash_between_digits(text):
    def replacer(matchobj):
        return '%s–%s' % (matchobj.group(1), matchobj.group(2))

    return re.sub(MIDDLE_DASH_BETWEEN_DIGITS_REGEXP, replacer, text)


CANONIC_DICT = {
    'Быт': 'Быт',
    'Исх': 'Исх',
    'Лев': 'Лев',
    'Чис': 'Чис',
    'Числ': 'Чис',
    'Втор': 'Втор',
    'Нав': 'Нав',
    'Суд': 'Суд',
    'Руф': 'Руф',
    'Цар': 'Цар',
    'Пар': 'Пар',
    'Паралип': 'Пар',
    'Неем': 'Неем',
    'Тов': 'Тов',
    'Иудиф': 'Иудиф',
    'Эсф': 'Эсф',
    'Мак': 'Мак',
    'Ездр': 'Ездр',
    'Иов': 'Иов',
    'Пс': 'Пс',
    'Притч': 'Притч',
    'Еккл': 'Еккл',
    'Песн': 'Песн',
    'Прем': 'Прем',
    'Сир': 'Сир',
    'Ис': 'Ис',
    'Иерем': 'Иер',
    'Вар': 'Вар',
    'Иезек': 'Иез',
    'Дан': 'Дан',
    'Ос': 'Ос',
    'Иоил': 'Иоил',
    'Ам': 'Ам',
    'Авд': 'Авд',
    'Ион': 'Ион',
    'Мих': 'Мих',
    'Наум': 'Наум',
    'Авв': 'Авв',
    'Соф': 'Соф',
    'Агг': 'Агг',
    'Зах': 'Зах',
    'Мал': 'Мал',
    'Мф': 'Мф',
    'Матф': 'Мф',
    'Мк': 'Мк',
    'Мрк': 'Мк',
    'Марк': 'Мк',
    'Лк': 'Лк',
    'Лук': 'Лк',
    'Ин': 'Ин',
    'Иоанн': 'Ин',
    'Деян': 'Деян',
    'Иак': 'Иак',
    'Петр': 'Петр',
    'Иоан': 'Ин',
    'Иуд': 'Иуд',
    'Рим': 'Рим',
    'Кор': 'Кор',
    'Гал': 'Гал',
    'Галл': 'Галл',
    'Еф': 'Еф',
    'Ефес': 'Еф',
    'Флп': 'Флп',
    'Кол': 'Кол',
    'Колос': 'Кол',
    'Сол': 'Сол',
    'Фес': 'Фес',
    'Фесс': 'Фес',
    'Тим': 'Тим',
    'Тимоф': 'Тимоф',
    'Тит': 'Тит',
    'Филим': 'Флм',
    'Евр': 'Евр',
    'Апок': 'Откр',
    'Откр': 'Откр',
    'Сирах': 'Сирах'}


def canonic_links(text):
    '''
    Silly descent parser for canonic licks

    :param text: text to parse
    :return: parsed text
    '''
    def format(token_list, index):
        result = {'result': '', 'context': token_list, 'start_index': index}

        if not token_list[index+1] == '.':  # dot should always be
            logging.warning('[WARN] Undotted: %s', token_list[index:index + 5])
            return

        if token_list[index] not in CANONIC_DICT:
            logging.warning('[WARN] Not in dict: %s', token_list[index:index + 5])
            return

        if token_list[index - 1].isdecimal():  # 1Петр.
            result['result'] += str(token_list[index - 1])
        else:
            result['start_index'] += 1

        result['result'] += CANONIC_DICT[token_list[index]]

        while index < len(token_list):
            index += 1
            token = token_list[index]

            if token == ')':
                break
            elif token == '.':
                result['result'] += '.'
            elif token in ('гл', 'ст'):  # Цар. гл. 13 == Цар. 13
                index += 1
            elif token == 'и':
                result['result'] += ','
            elif token == ';':
                result['result'] += ';'
            elif token.isdecimal():
                result['result'] += token
            elif token == ',':
                if ':' not in result['result']:
                    result['result'] += ':'
                elif ';' in result['result']:
                    result['result'] += ':'
                else:
                    result['result'] += ','
            elif re.match(r'\d+–\d+', token):
                result['result'] += token
            elif re.match(r'\d+,\d+', token):
                result['result'] += token.replace(',', ':')
            else:
                break

        result['final_index'] = index - 3
        for symbol in '.,:':
            result['result'] = result['result'].rstrip(symbol)

        return result

    keywords = set(CANONIC_DICT.keys())
    keywords.update(CANONIC_DICT.values())

    offset = 0
    word_spans = []
    for token in nltk.word_tokenize(text):
        offset = text.find(token, offset)
        word_spans.append((token, offset, offset + len(token)))
        offset += len(token)

    changes = []
    for i, word_span in enumerate(word_spans):
        if word_span[0] in keywords:
            st_in = i - 2
            end_in = i + 30

            result = format([x[0] for x in word_spans[st_in:end_in]], 2)

            if result:
                st_offset = word_spans[i + result['start_index'] - 3][1]  # offsets are positions in text
                end_offset = word_spans[i + result['final_index']][2]  # indexes are numbers of tokens
                logging.info('[CHANGED] %s -> %s', text[st_offset:end_offset], result['result'])
                logging.debug('[DEBUG] %s ', result)
                changes.append((st_offset, end_offset, result['result']))

    return text
