#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

_whitespace_cleanup = re.compile('[ ]*\n', re.MULTILINE)
def whitespace_cleanup(x):
    return _whitespace_cleanup.sub('\n', x)

def common_prefix(m):
    """
    Longest common prefix.

    >>> common_prefix(['prefix-a', \
                       'prefix-b', \
                       'prefix-c'])
    'prefix-'

    """
    if not m:
        return ''
    s1 = min(m)
    s2 = max(m)
    for i, c in enumerate(s1):
        if c != s2[i]:
            return s1[:i]
    return s1


# Borrowed from: http://www.codigomanso.com/en/2010/05/una-de-python-force_unicode/
def force_unicode(s, encoding='utf-8', errors='ignore'):
    """
    Returns a unicode object representing 's'. Treats bytestrings using the
    'encoding' codec.
    """
    if s is None:
        return ''
    try:
        if not isinstance(s, str,):
            if hasattr(s, '__unicode__'):
                s = str(s)
            else:
                try:
                    s = str(str(s), encoding, errors)
                except UnicodeEncodeError:
                    if not isinstance(s, Exception):
                        raise
                    # If we get to here, the caller has passed in an Exception
                    # subclass populated with non-ASCII data without special
                    # handling to display as a string. We need to handle this
                    # without raising a further exception. We do an
                    # approximation to what the Exception's standard str()
                    # output should be.
                    s = ' '.join(force_unicode(arg, encoding, errors) for arg in s)
        elif not isinstance(s, str):
            # Note: We use .decode() here, instead of unicode(s, encoding,
            # errors), so that if s is a SafeString, it ends up being a
            # SafeUnicode at the end.
            s = s.decode(encoding, errors)
    except UnicodeDecodeError as e:
        if not isinstance(s, Exception):
            raise UnicodeDecodeError (s, *e.args)
        else:
            # If we get to here, the caller has passed in an Exception
            # subclass populated with non-ASCII bytestring data without a
            # working unicode method. Try to handle this without raising a
            # further exception by individually forcing the exception args
            # to unicode.
            s = ' '.join(force_unicode(arg, encoding, errors) for arg in s)
    return str(s)


def PRE(x):
    return '<pre>' +  x.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') + '</pre>'


# native, HTML, default Unicode (Code page 850), Unicode combined Character, Windows-1250
"""
_recodings = {'ae': ['ä', u'ä', '&auml;', '\\u00E4', u'\\u00E4', '\\u0308a', '\xc3\xa4'],
              'oe': ['ö', u'ö', '&ouml;', '\\u00F6', u'\\u00F6', '\\u0308o', '\xc3\xb6'],
              'ue': ['ü', u'ü', '&uuml;', '\\u00FC', u'\\u00FC', '\\u0308u', '\xc3\xbc'],
              'Ae': ['Ä', u'Ä', '&Auml;', '\\u00C4', u'\\u00C4', '\\u0308A', '\xc3\x84'],
              'Oe': ['Ö', u'Ö', '&Ouml;', '\\u00D6', u'\\u00D6', '\\u0308O', '\xc3\x96'],
              'Ue': ['Ü', u'Ü', '&Uuml;', '\\u00DC', u'\\u00DC', '\\u0308U', '\xc3\x9c'],
              'ss': ['ß', u'ß', '&szlig;', '\\u00DF', u'\\u00DF', '\xc3\x9f'],
              'e': ['é', u'é', '\xc3\xa9'],
             }
"""

# taken from NLTK
def htmltotext(x):
    """ Remove HTML markup from the given string. """
    # remove inline JavaScript / CSS
    x = re.compile('<script.*?>[\w\W]*?</script>', re.IGNORECASE).sub('', x)
    x = re.compile('<style.*?>[\w\W]*?</style>', re.IGNORECASE).sub('', x)
    # remove html comments. must be done before removing regular tags since comments can contain '>' characters.
    x = re.sub(r'<!--([\w\W]*?)-->', '', x)
    # remove the remaining tags
    x = re.sub(r'(?s)<.*?>', ' ', x)
    # remove html entities
    x = remove_entities(x)
    # clean up whitespace
    x = re.sub('[ ]+', ' ', x)
    x = re.compile('(\n\n+)', re.MULTILINE).sub('\n', x)
    return x


import unicodedata
def strip_accents(s):
    """ Transform accentuated unicode symbols into their simple counterpart. """
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))

# iso-8859-1
LATIN2ASCII = {
    # uppercase
    '\u00c0': 'A`',
    '\u00c1': "A'",
    '\u00c2': 'A^',
    '\u00c3': 'A~',
    '\u00c4': 'A:',
    '\u00c5': 'A%',
    '\u00c6': 'AE',
    '\u00c7': 'C,',
    '\u00c8': 'E`',
    '\u00c9': "E'",
    '\u00ca': 'E^',
    '\u00cb': 'E:',
    '\u00cc': 'I`',
    '\u00cd': "I'",
    '\u00ce': 'I^',
    '\u00cf': 'I:',
    '\u00d0': "D'",
    '\u00d1': 'N~',
    '\u00d2': 'O`',
    '\u00d3': "O'",
    '\u00d4': 'O^',
    '\u00d5': 'O~',
    '\u00d6': 'O:',
    '\u00d8': 'O/',
    '\u00d9': 'U`',
    '\u00da': "U'",
    '\u00db': 'U~',
    '\u00dc': 'U:',
    '\u00dd': "Y'",
    '\u00df': 'ss',
    # lowercase
    '\u00e0': 'a`',
    '\u00e1': "a'",
    '\u00e2': 'a^',
    '\u00e3': 'a~',
    '\u00e4': 'a:',
    '\u00e5': 'a%',
    '\u00e6': 'ae',
    '\u00e7': 'c,',
    '\u00e8': 'e`',
    '\u00e9': "e'",
    '\u00ea': 'e^',
    '\u00eb': 'e:',
    '\u00ec': 'i`',
    '\u00ed': "i'",
    '\u00ee': 'i^',
    '\u00ef': 'i:',
    '\u00f0': "d'",
    '\u00f1': 'n~',
    '\u00f2': 'o`',
    '\u00f3': "o'",
    '\u00f4': 'o^',
    '\u00f5': 'o~',
    '\u00f6': 'o:',
    '\u00f8': 'o/',
    '\u00f9': 'o`',
    '\u00fa': "u'",
    '\u00fb': 'u~',
    '\u00fc': 'u:',
    '\u00fd': "y'",
    '\u00ff': 'y:',
}


LIGATURES_PAIRS = [
    ('ﬃ', 'ffi'),
    ('ﬀ', 'ff'),
    ('ﬁ', 'fi'),
    ('ﬂ', 'fl'),

    ('—', '--'),
    ('–', '-'),

    ('“', '"'),
    ('”', '"'),

    (" ", " "),
    ("’", "'"),
    ("•", "*"),
    ("…", "..."),

    ('\u00c6', 'AE'),
    ('\u00e6', 'ae'),
    ('\u0152', 'OE'),
    ('\u0153', 'oe'),
    ('\u0132', 'IJ'),
    ('\u0133', 'ij'),
    ('\u1d6b', 'ue'),
    ('\ufb00', 'ff'),
    ('\ufb01', 'fi'),
    ('\ufb02', 'fl'),
    ('\ufb03', 'ffi'),
    ('\ufb04', 'ffl'),
    ('\ufb05', 'ft'),
    ('\ufb06', 'st'),
]

LIGATURES_MAP = dict(LIGATURES_PAIRS)

LIGATURES = re.compile('(%s)' % '|'.join(k for k,v in LIGATURES_PAIRS))


#import unicodedata
#>>> source = u'Mikael Håfström'
#>>> unicodedata.normalize('NFKD', source).encode('ascii', 'ignore')
def normalize(text):
    """
    >>> normalize(u'Efﬁciently')
    u'Efficiently'
    """
    text = force_unicode(text)
    return unicodedata.normalize('NFKD', text) #.encode('ascii', 'ignore')


def remove_ligatures(text):
    """
    >>> remove_ligatures(u'Efﬁciently')
    u'Efficiently'
    """
    text = normalize(text)   # or at least force_unicode
    return LIGATURES.sub(lambda m: LIGATURES_MAP[m.group(1)], text)


def convert_special_html_escapes(text):
    for plain, funny in (('ä','&auml;'), ('ö','&ouml;'), ('ü','&uuml;'), ('Ä','&Auml;'), ('Ö','&Ouml;'),
                         ('Ü','&Uuml;'), ('ß','&szlig;')):
        text = text.replace(funny, plain)
    return text


def remove_html_escapes(text):
    for plain, funny in (('&','&amp;'), ('<','&lt;'), ('>','&gt;'), ('"','&quot;'), ("'",'&#39;')):
        text = text.replace(funny, plain)
    return text


def remove_latin(text):
    text = text.encode('utf-8')
    text = str(text)
    # chars that ISO-8859-1 does not support
    for plain, funny_set in (
                             ('"', '“”'),
                             ('-', '\u2013\u2014\u2022'),
                             ("'", '\u2018\u2019'),
                             ('', '\ufffd\u2122\u2020'),
                             ('...', '\u2026'),
#                             ('i', u'\u012b'),
#                             ('ã', u'\u0101'),
#                             ('r', u'\u0159'),
#                             ('Z',u'\u017d'),
#                             ('z', u'\u017e'),
                             ('EUR', '\u20ac')):
        for funny in funny_set:
            orig = text
            text = text.replace(funny, plain)
            if orig != text:
                print('XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX')
                print(funny, '->', plain)
                print(list(funny_set))
                print(text)
                print('XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX')
    return text

def remove_accents(text):
    text = str(text).encode('utf-8')
    for plain, funny_set in (('a','áàâãäå\\u0101'), ('e','éèêẽë'), ('i',"íìîĩï"), ('o','óòôõöø'),
                             ('u',"úùûũü"), ('A','ÁÀÂÃÄÅ'), ('E','ÉÈÊẼË'), ('I',"ÍÌÎĨÏ"),
                             ('O','ÓÒÔÕÖØ'), ('U',"ÚÙÛŨÜ"), ('n',"ñ"), ('c',"ç"), ('N',"Ñ"),
                             ('C',"Ç"), ('d',"Þ"), ('ss',"ß"), ('ae',"æ"), ('oe','œ')):
        for funny in funny_set:
            text = text.replace(funny, plain)
    return text



"""
=========================================================================================
Functions for dealing with markup text

Taken from scrapy
"""

#import re
from html.entities import name2codepoint

def str_to_unicode(text, encoding=None):
    """Return the unicode representation of text in the given encoding. Unlike
    .encode(encoding) this function can be applied directly to a unicode
    object without the risk of double-decoding problems (which can happen if
    you don't use the default 'ascii' encoding)
    """

    if encoding is None:
        encoding = 'utf-8'
    if isinstance(text, str):
        return text.decode(encoding)
    elif isinstance(text, str):
        return text
    else:
        raise TypeError('str_to_unicode must receive a str or unicode object, got %s' % type(text).__name__)

def unicode_to_str(text, encoding=None):
    """Return the str representation of text in the given encoding. Unlike
    .encode(encoding) this function can be applied directly to a str
    object without the risk of double-decoding problems (which can happen if
    you don't use the default 'ascii' encoding)
    """

    if encoding is None:
        encoding = 'utf-8'
    if isinstance(text, str):
        return text.encode(encoding)
    elif isinstance(text, str):
        return text
    else:
        raise TypeError('unicode_to_str must receive a unicode or str object, got %s' % type(text).__name__)


_ent_re = re.compile(r'&(#?(x?))([^&;\s]+);')
_tag_re = re.compile(r'<[a-zA-Z\/!].*?>', re.DOTALL)

def remove_entities(text, keep=(), remove_illegal=True, encoding='utf-8'):
    """Remove entities from the given text.

    'text' can be a unicode string or a regular string encoded in the given
    `encoding` (which defaults to 'utf-8').

    If 'keep' is passed (with a list of entity names) those entities will
    be kept (they won't be removed).

    It supports both numeric (&#nnnn; and &#hhhh;) and named (&nbsp; &gt;)
    entities.

    If remove_illegal is True, entities that can't be converted are removed.
    If remove_illegal is False, entities that can't be converted are kept "as
    is". For more information see the tests.

    Always returns a unicode string (with the entities removed).
    """

    def convert_entity(m):
        entity_body = m.group(3)
        if m.group(1):
            try:
                if m.group(2):
                    number = int(entity_body, 16)
                else:
                    number = int(entity_body, 10)
                # Numeric character references in the 80-9F range are typically
                # interpreted by browsers as representing the characters mapped
                # to bytes 80-9F in the Windows-1252 encoding. For more info
                # see: http://en.wikipedia.org/wiki/Character_encodings_in_HTML
                if 0x80 <= number <= 0x9f:
                    return chr(number).decode('cp1252')
            except ValueError:
                number = None
        else:
            if entity_body in keep:
                return m.group(0)
            else:
                number = name2codepoint.get(entity_body)
        if number is not None:
            try:
                return chr(number)
            except ValueError:
                pass

        return '' if remove_illegal else m.group(0)

    return _ent_re.sub(convert_entity, str_to_unicode(text, encoding))

def has_entities(text, encoding=None):
    return bool(_ent_re.search(str_to_unicode(text, encoding)))

def replace_tags(text, token='', encoding=None):
    """Replace all markup tags found in the given text by the given token. By
    default token is a null string so it just remove all tags.

    'text' can be a unicode string or a regular string encoded as 'utf-8'

    Always returns a unicode string.
    """
    return _tag_re.sub(token, str_to_unicode(text, encoding))


def remove_comments(text, encoding=None):
    """ Remove HTML Comments. """
    return re.sub('<!--.*?-->', '', str_to_unicode(text, encoding), re.DOTALL)

def remove_tags(text, which_ones=(), keep=(), encoding=None):
    """ Remove HTML Tags only.

        which_ones and keep are both tuples, there are four cases:

        which_ones, keep (1 - not empty, 0 - empty)
        1, 0 - remove all tags in which_ones
        0, 1 - remove all tags except the ones in keep
        0, 0 - remove all tags
        1, 1 - not allowd
    """

    assert not (which_ones and keep), 'which_ones and keep can not be given at the same time'

    def will_remove(tag):
        if which_ones:
            return tag in which_ones
        else:
            return tag not in keep

    def remove_tag(m):
        tag = m.group(1)
        return '' if will_remove(tag) else m.group(0)

    regex = '</?([^ >/]+).*?>'
    retags = re.compile(regex, re.DOTALL | re.IGNORECASE)

    return retags.sub(remove_tag, str_to_unicode(text, encoding))

def remove_tags_with_content(text, which_ones=(), encoding=None):
    """ Remove tags and its content.

        which_ones -- is a tuple of which tags with its content we want to remove.
                      if is empty do nothing.
    """
    text = str_to_unicode(text, encoding)
    if which_ones:
        tags = '|'.join([r'<%s.*?</%s>|<%s\s*/>' % (tag, tag, tag) for tag in which_ones])
        retags = re.compile(tags, re.DOTALL | re.IGNORECASE)
        text = retags.sub('', text)
    return text


def replace_escape_chars(text, which_ones=('\n', '\t', '\r'), replace_by='', \
        encoding=None):
    """ Remove escape chars. Default : \\n, \\t, \\r

        which_ones -- is a tuple of which escape chars we want to remove.
                      By default removes \n, \t, \r.

        replace_by -- text to replace the escape chars for.
                      It defaults to '', so the escape chars are removed.
    """
    for ec in which_ones:
        text = text.replace(ec, str_to_unicode(replace_by, encoding))
    return str_to_unicode(text, encoding)

def unquote_markup(text, keep=(), remove_illegal=True, encoding=None):
    """
    This function receives markup as a text (always a unicode string or a utf-8 encoded string) and does the following:
     - removes entities (except the ones in 'keep') from any part of it that it's not inside a CDATA
     - searches for CDATAs and extracts their text (if any) without modifying it.
     - removes the found CDATAs
    """
    _cdata_re = re.compile(r'((?P<cdata_s><!\[CDATA\[)(?P<cdata_d>.*?)(?P<cdata_e>\]\]>))', re.DOTALL)

    def _get_fragments(txt, pattern):
        offset = 0
        for match in pattern.finditer(txt):
            match_s, match_e = match.span(1)
            yield txt[offset:match_s]
            yield match
            offset = match_e
        yield txt[offset:]

    text = str_to_unicode(text, encoding)
    ret_text = ''
    for fragment in _get_fragments(text, _cdata_re):
        if isinstance(fragment, str):
            # it's not a CDATA (so we try to remove its entities)
            ret_text += remove_entities(fragment, keep=keep, remove_illegal=remove_illegal)
        else:
            # it's a CDATA (so we just extract its content)
            ret_text += fragment.group('cdata_d')
    return ret_text


if __name__ == '__main__':
    import sys
    if sys.stdin.isatty():
        sys.exit(1)
    print(remove_ligatures(sys.stdin.read()).encode('ascii', 'ignore'))
