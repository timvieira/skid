# -*- coding: utf-8 -*-
import re

try:
    from fabulous.color import fg256
except ImportError:
    def color(c, x):
        "Colorize numbers in [0,1] based on value; darker means smaller value."
        return unicode(x).encode('utf8')
else:
    def color(c, x):
        "Colorize numbers in [0,1] based on value; darker means smaller value."
        a, b = 238, 255   # 232, 255
        w = b - a
        offset = x*w
        offset = int(round(offset))
        return unicode(fg256(a + offset, c)).encode('utf8')


from whoosh.analysis import STOP_WORDS


re_stopwords = re.compile(r'\b(%s)\b\s*' % '|'.join(STOP_WORDS), re.I)
def remove_stopwords(x):
    """
    >>> remove_stopwords('A man saw the boy with his telescope.')
    'man saw boy his telescope.'
    """
    return re_stopwords.sub('', x)


def lastname(name):
    """
    Extract author last name from string `name`.

    TODO: Cover "Lastname, First M."
    TODO: Consider using a name parser

    Ignores roman numeral suffixes.

    >>> print lastname("John Doe VI")
    Doe
    """
    return [w for w in name.strip().split() if not re.match('^[VIX]+$',w)][-1]


def author(x):
    """
    Format an ordered list author names.

    >>> author(['Ves Stoyanov', 'Alexander Ropson', 'Jason Eisner'])
    'Stoyanov et al.'

    >>> print author(['Hal Daumé III', 'Jason Eisner'])
    Daumé & Eisner
    """

    if not x:
        return ''

    last = map(lastname, x)

    if len(last) == 1:
        return '%s' % last[0]
    elif len(last) == 2:
        return '%s & %s' % (last[0], last[1])
    else:
        return '%s+' % (last[0])


def shingle(x, n=3):
    """
    Explode a string into sequence of n-grams.

    >>> shingle("abcdef", n=3)
    ['abc', 'bcd', 'cde', 'def']
    """
    return [x[i:i+n] for i in xrange(0, len(x) - n+1)]


def bibkey(x):
    """

    >>> bibkey('bottou12counterfactual')
    ('bottou', '*12', 'counterfactual')

    >>> bibkey('bottou12')
    ('bottou', '*12', '')

    >>> bibkey('bottou')

    >>> bibkey('bottou2012')
    ('bottou', '2012', '')

    """
    try:
        [(author, year, title)] = re.findall('([a-z]+)(\d{4}|\d{2})([a-z]*)', x)
        if len(year) == 2:
            year = '*' + year
        return (author, year, title)
    except ValueError:
        pass
