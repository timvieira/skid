#!/usr/bin/env python
import re, sys, unittest

#------------------------------------------------------------------------------
DEBUG = 0
from contextlib import contextmanager
from arsenal.misc import ctx_redirect_io
@contextmanager
def verbose():
    global DEBUG
    DEBUG = 1
    try:
        with ctx_redirect_io() as io:
            yield
    except:
        raise
    else:
        print colors.yellow % io.getvalue()
    finally:
        DEBUG = 0

        sys.stdout.flush()

import arsenal.terminal.colors as colors
Fail = colors.red % 'FAIL'
Pass = colors.green % 'pass'
YES = colors.bold % '  = YES ==='
NO = colors.bold % '  = NO ==='
#------------------------------------------------------------------------------


from arsenal.nlp.wordsplitter import wordsplit_sentence
def wordsplit(text):
    text = re.sub('[a-z]\?[a-z]', '', text)   # special case fi => \002 => ?
    return wordsplit_sentence(text).split()

# pre-compiled regular expressions
from arsenal.nlp.patterns import URL_RE, EMAIL_RE
NONALPHA = re.compile('[^a-zA-Z]')
SPACES = re.compile('\s+')
DIGIT = re.compile('[0-9]')
PUNC = re.compile('[!"%&\'()*+,./:;<=>?@[\\]^_`{|}~]')
LOWERCASE = re.compile('([a-z]+)')
UPPERCASE = re.compile('([A-Z]+)')

from arsenal.nlp.features import pattern

zipcode = pattern("[0-9]{5}(?:-[0-9]{4})?")
phoneorzip = pattern('[0-9]+-[0-9]+')
areacode = pattern('\(\d{3}\)')
phone = pattern('(?:\(?\d{3}\)?-?)?\d{3}-\d{4}')
acronym = pattern('[A-Z][A-Z\.]*\.[A-Z\\.]*')
def email(text): return bool(EMAIL_RE.match(text.replace(' ', '')))
def url(text): return bool(URL_RE.match(text))


def get_lexicon(x):
    return frozenset(x.strip().split() if isinstance(x, (str, unicode)) else x)

# Name lexicon features
from arsenal.nlp.lexicon.names import male, female, last
first_names = get_lexicon(male.male_names) | get_lexicon(female.female_names)
last_names = get_lexicon(last.last_names)
firstname = first_names.__contains__
lastname = last_names.__contains__

from arsenal.nlp.lexicon.stopwords import stopwords
stopwords = get_lexicon(stopwords)
def is_stopword(w):
    return w.lower() in stopwords or not (1 < len(w) <= 25)
def not_stopword(w):
    return not is_stopword(w)
def remove_stopwords(text):
    return filter(not_stopword, text.split())

from arsenal.nlp.lexicon.honorifics import honorifics
honorifics = honorifics.__contains__

# Postal address lexicons.
#   Note: these features assume lowercase inputs
from arsenal.nlp.lexicon.postal_abbrev import postal_abbrev
from arsenal.nlp.lexicon.address import cardinal_direction
postal_abbrev = postal_abbrev.__contains__
cardinal_direction = cardinal_direction.__contains__

from arsenal.nlp.lexicon import state_abbrev
state_abbr_normalizer = \
    dict((x, abbr[0]) for abbr in state_abbrev.more_abbreviations for x in abbr[1:4])

def simplify(w):
    # state names and common abbrevs -> postal abbreviation
    if w in state_abbr_normalizer:
        w = state_abbr_normalizer[w]
    elif (w+'.') in state_abbr_normalizer:
        w = state_abbr_normalizer[w + '.']
    # stem variations of "University" -> "univ"
    w = re.sub('([Uu]niv(?:ersity|\.|))', 'univ', w)
    w = w.lower()
    w = NONALPHA.sub('', w)
    return w

from arsenal.nlp.lexicon.universities import universities
def normalize_university(x):
    return frozenset(simplify(w) for w in remove_stopwords(re.sub('[^a-zA-Z\. ]', ' ', x)))
universities = set(normalize_university(x[-1]) for x in universities)

from arsenal.nlp.features import possible_year, doftw, month, time, digits, punct, \
    numeric, written_number, ordinal, abbrev, initial, roman

def stem(w):
    if w in ('A.D.','B.C'):   return 'ADBC'
    if w == ',':              return 'COMMA'
    if numeric(w):            return 'NUMERIC'
    if doftw(w):              return 'DOFTW'
    if month(w):              return 'MONTH'
    if written_number(w):     return 'WRITTEN-NUMBER'
    if ordinal(w):            return 'ORDINAL'
    if time(w):               return 'TIME'
    if areacode(w):           return 'AREACODE'
    if phone(w):              return 'PHONE'
    w = w.lower()
    if cardinal_direction(w): return 'CARDINAL-DIRECTION'
    return DIGIT.sub('#', PUNC.sub('@', w))


year_in_parens = pattern("\(\s*[0-9][0-9][0-9][0-9][a-z]?\s*\)")
possible_page = pattern("[0-9]+\s*\-\s*[0-9]+")
possible_volume = pattern("[0-9][0-9]?\s*\([0-9]+\)")


def token_features(tk):
    W = tk.form
    w = W.lower()
    yield '[stem="%s"]' % stem(w)
    # use upper case word
    #yield '[letter-pattern="%s"]'  % letter_pattern(W)
    if firstname(W):        yield '[firstname]'
    if lastname(W):         yield '[lastname]'
    if roman(W):            yield '[roman-numeral]'
    if initial(W):          yield '[is-initial]'
    if abbrev(W):           yield '[abbrev]'
    if acronym(W):          yield '[acronym-like]'
    if honorifics(W):       yield '[honorific]'
    # use lower case word
    if w.startswith('http://'): yield '[startswith="http://"]'
    if postal_abbrev(w):    yield '[postal_abbrev]'
    # doesn't care what the case is
    if email(w):            yield '[email]'
    if url(w):              yield '[url]'
    if zipcode(w):          yield '[zipcode]'
    if possible_year(w):    yield '[possible-year]'
    if digits(w):
        yield '[is-digits]'
        yield '[%s-digit]' % min(len(w), 5)

    if digits.contains(w):  yield '[contains-digits]'
    if numeric.contains(w): yield '[contains-numeric]'
    if punct(w):            yield '[is-punct]'
    if punct.contains(w):   yield '[contains-punct]'
    if '.' in w:            yield '[contains-dot]'
    if '-' in w:            yield '[contains-dash]'
    if phoneorzip(w):       yield '[phone-or-zip]'

    if year_in_parens(w):   yield '[year-in-parens]'
    if possible_page(w):    yield '[possible-page]'
    if possible_volume(w):  yield '[possible-volume]'

    #RegexMatchOrNot("PAGEWORDS",   "(?:pp\.|[Pp]ages?|[\-,\.()]|[0-9]\s+)+")

    #RegexMatcher("LONELYINITIAL",  CAPS+"\."),
    #RegexMatcher("SINGLECHAR",     ALPHA),
    #RegexMatcher("CAPLETTER",      "[A-Z]"),
    #RegexMatcher("ALLCAPS",        CAPS+"+"),
    #RegexMatcher("INITCAP",        CAPS+".*")


# LexResource("FIRSTHIGHEST", "ner/conllDict/personname/ssdi.prfirsthighest"),
# LexResource("FIRSTHIGH",    "ner/conllDict/personname/ssdi.prfirsthigh"),
# LexResource("FIRSTMED",     "ner/conllDict/personname/ssdi.prfirstmed"),
# LexResource("FIRSTLOW",     "ner/conllDict/personname/ssdi.prfirstlow"),

# LexResource("LASTHIGHEST",  "ner/conllDict/personname/ssdi.prlasthighest"),
# LexResource("LASTHIGH",     "ner/conllDict/personname/ssdi.prlasthigh"),
# LexResource("LASTMED",      "ner/conllDict/personname/ssdi.prlastmed"),
# LexResource("LASTLOW",      "ner/conllDict/personname/ssdi.prlastlow"),

# LexResource("HONORIFIC",    "ner/conllDict/personname/honorifics"),
# LexResource("NAMESUFFIX",   "ner/conllDict/personname/namesuffixes"),
# LexResource("NAMEPARTICLE", "ner/conllDict/personname/name-particles"),

# LexResource("PLACESUFFIX",  "ner/conllDict/place-suffixes"),
# LexResource("STOPWORD",     "ner/conllDict/stopwords"),
# LexResource("STREETHIGH",   "casutton/streets_high"),
# LexResource("STREETALL",    "casutton/streets_all"),
# LexResource("ROOM",         "casutton/rooms"),

# LexResource("COUNTRY",      "ner/conllDict/countries")
# LexResource("USSTATE",      "ner/conllDict/US-states")
# LexResource("USSTATEABBR",  "rexa/state_abbreviations")

# LexResource("DBLPTITLESTARTHIGH", "rexa/title.start.high"),
# LexResource("DBLPTITLESTARTMED",  "rexa/title.start.med"),
# LexResource("DBLPTITLEHIGH",      "rexa/title.high"),
# LexResource("DBLPTITLEMED",       "rexa/title.med"),
# LexResource("DBLPTITLELOW",       "rexa/title.low"),
# LexResource("DBLPAUTHORFIRST",    "rexa/author-first",     ignore_case=False),
# LexResource("DBLPAUTHORMIDDLE",   "rexa/author-middle",    ignore_case=False),
# LexResource("DBLPAUTHORLAST",     "rexa/author-last",      ignore_case=False),
# LexResource("DBLPPUBLISHER",      "rexa/publisher",        ignore_case=False),
# LexResource("CONFABBR",           "rexa/conferences.abbr")
# LexResource("CONFFULL",           "rexa/conferences.full"),
# LexResource("JOURNAL",            "rexa/journals")

#_________________
# Patterns
def one_or_more(a):
    plus = a + '+'
    return lambda m: (plus if len(m.group(1)) > 1 else a)

OTHER = re.compile("[^\w?+'\-,./\s@()]")

def letter_pattern(text):
    text = UPPERCASE.sub(one_or_more('A'), text)
    text = LOWERCASE.sub(one_or_more('a'), text)
    text = DIGIT.sub('8', text)
    text = SPACES.sub(' ', text)
    text = OTHER.sub('?', text)
    return text

#_________________________
# universities

def is_university(x):
    w = normalize_university(x)
    if DEBUG:
        print '      * normalized:', w

    if 'univ' in w or 'college' in w:
        if DEBUG:
            print '      * SPECIAL CASE:'
        # TODO: do this more efficiently
        for x in universities:
            if len(w.intersection(x)) > 1:
                if DEBUG:
                    print '       ', w, x, w.intersection(x)
                return True
        return False
    return w in universities

#________________________
# titles
def title_shaped(text):   # XXX: should single words be a special case?
    if isinstance(text, basestring):
        text = text.strip()
    nostop = remove_stopwords(text)
    if DEBUG:
        print '      * no-stopwords:', nostop
        print '      * isupper-w[0]:', [w[0].isupper() for w in nostop]
    if len(nostop) < 1 or not nostop[0][0].isupper():
        return False
    return all(w[0].isupper() for w in nostop if w.isalpha())

#_______________________
# unit tests

FUTURE = 1

class FeaturesTests(unittest.TestCase):

    @staticmethod
    def assertEQ(f, args, target):
        if not isinstance(args, (tuple,list)):
            args = (args,)
        result = f(*args)

        if result == target:
            print '  %-65r' % args[0], Pass
        else:
            print '  %-65r' % args[0], Fail

        if result != target:
            with verbose():
                result = f(*args)
        return result == target

    def yes_no_template(self, f, yes, no):
        print
        print f.__name__
        print YES
        for x in yes:
            self.assertEQ(f, x, True)
        print NO
        for x in no:
            self.assertEQ(f, x, False)

    def test_is_university(self):
        self.yes_no_template(is_university, (
                'University of Illinois at Champaign - Urbana',
                'University of Illinois at Urbana - Champaign',
                'University of Massachusetts at Amherst',
                'University of Massachusetts Amherst',
                'Univ of Massachusetts - Amherst',
                'Univ. of Massachusetts - Amherst',
                'University of Mass. at Amherst',
                'University of Mass. - Amherst',
                'University of Mass - Amherst',
                'University of Massachusetts',
                'University of Mass.',
                'University of Mass',
            ), (
                '',
                'Massachusetts',
                'Illinois',
                'University',
                'John Doe',
                'with',
                'the',
                'Mass',
                'Amherst, Massachusetts'
            ))

    if FUTURE:
        def test_FUTURE_univ(self):
            self.yes_no_template(is_university, (
                'Tsinghua University',
                ), ())

#        def test_FUTURE_names(self):
#            self.yes_no_template(contains_first_name, (
#                'Fuchun Peng',
#                ), ())

    def test_title_shaped(self):
        self.yes_no_template(title_shaped, (
                'Multi-hop Radio Networks',
                'University of Massachusetts',
                'University of Mass - Amherst',
                'University of Mass',
                'The Great Gatsby',
                'Declaration of Independence of the United States of America',
                'with High-Order Representations',
                'Generalized Expectation Criteria',
                'MapReduce: Simpli?ed Data Processing on Large Clusters',
            ), (
                '',
                'the'
                'hello',
            ))

#    def test_contains_first_name(self):
#        self.yes_no_template(contains_first_name, (
#                'Timothy F. Vieira',
#                'Andrew McCallum',
#                'Adam Saunders',
#                'Andrew McCallum, Gideon Mann, Gregory Druck',
#            ), (
#                '',
#                'In this paper, however, we experiment with several alter-',
#                'hello',
#                'University of Mass',
#                'The Great Gatsby',
#                'Declaration of Independence of the United States of America',
#            ))

#    def test_contains_last_name(self):
#        self.yes_no_template(contains_last_name, (
#                'Timothy F. Vieira',
#                'Andrew McCallum',
#                'Adam Saunders',
#                'Andrew McCallum, Gideon Mann, Gregory Druck',
#            ), (
#                '',
#                'Backing Off: Hierarchical Decomposition of Activity for 3D Novel Pose Recovery',
#                'In this paper, however, we experiment with several alter-',
#                'hello',
##                'University of Mass',
#                'The Great Gatsby',
##                'Declaration of Independence of the United States of America',
#            ))

    def test_url(self):
        self.yes_no_template(url, (
                'google.com',
                'http://google.co.uk',
                'https://www.google.com',
                'http://cs.umass.edu/~timv/index.html',
                'http://www.rexa.info',
                'http://jasper.cs.umass.edu:80/new-textmill',
                'ftp://johndoe.com/file.txt',
                'http://blahblah.co.uk',
                'blahblah.com.br',
            ), (
                '',
                'hello',
                '.com/',
                'http://',
                # try out the emails, none of these should be urls.

            ) + self.Emails)

    Emails = (
        '{timsfanmail|tim.f.vieira, timv}@gmail.com',
        '{timsfanmail|tim.f.vieira,timv}@gmail.com',
        'timsfanmail@yahoo.com',
        'timv@cs.umass.edu',
        'mailto://timv@cs.umass.edu',
        '{mccallum,gmann,gdruck}@cs.umass.edu',
    )

    def test_email(self):
        self.yes_no_template(email, self.Emails, (
                '',
                'umass.edu',
                '@',
                'as',
                'foo@.com',
                'foo@com',
            ))


if __name__ == '__main__':
    unittest.main()

# Department of Computer Science
# Amherst, MA 01003 USA
