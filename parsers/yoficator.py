"""
Simple yoficator
Dict from https://raw.githubusercontent.com/unabashed/yoficator/master/yoficator.dic
"""
import nltk
import os


def _load_dict(file):
    with open(file) as file_h:
        yo_dict_loaded = {}

        for line in file_h.readlines():
            k, v = line.split(':')
            yo_dict_loaded[k] = v

    return yo_dict_loaded


yo_dict = _load_dict(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'yoficator.dic.txt'))


def yoficator(text):
    tokens = nltk.word_tokenize(text)
    changes = [token for token in tokens if token in yo_dict]
    for change in changes:
        text = text.replace(' ' + change + ' ', ' ' + yo_dict[change].strip() + ' ')

    return text
