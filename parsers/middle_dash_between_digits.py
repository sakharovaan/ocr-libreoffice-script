import re
import logging
import nltk
import string

MIDDLE_DASH_BETWEEN_DIGITS_REGEXP = re.compile(r'(\d+)\s*[-—–]\s*(\d+)', re.MULTILINE)


def middle_dash_between_digits(text):
    def replacer(matchobj):
        return '%s–%s' % (matchobj.group(1), matchobj.group(2))

    return re.sub(MIDDLE_DASH_BETWEEN_DIGITS_REGEXP, replacer, text)
