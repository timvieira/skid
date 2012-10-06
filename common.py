import re
from text.utils import force_unicode
from terminal import blue, yellow
from pprint import pformat


def parse_notes(notes):
    """

    Need to evaluate alternatives here.

    ========================================
    org-mode seems to want something like:

    #+title: Meta-Syntactic Variables

    :PROPERTIES:
      :title: Meta-Syntactic Variables
      :author: Foo B. Baz
      :year: 2012
    :END:

    =======================================

    I love that org-mode super developed for emacs, but some of the syntax
    really needs revisiting... It's also pretty difficult for me to extend
    because I'm terrible with elisp.

    """

    # need to support multiple write to same key.
    metadata = dict(re.findall('^(?:\#\+?|:)([^:\s]+):[ ]*([^\n]*?)\s*$', notes, re.MULTILINE))

    ##     msg = """\
    ## \033[31m<parse_notes>\033[0m
    ## \033[31m<data>\033[0m
    ## %s
    ## \033[31m</data>\033[0m
    ##
    ## \033[31m<metdata>\033[0m
    ## %s
    ## \033[31m</metadata>\033[0m
    ## \033[31m</parsedata>\033[0m
    ## """ % (yellow % notes, pformat(metadata))
    ##     print msg

    [d] = re.findall('\n([^:#][\w\W]*$|$)', notes)
    metadata['description'] = d.strip()

    # TODO: we need to use a real metadata markup language with a fast parser and
    # easy greping

    return unicodify_dict(metadata)


def test_parse_notes(filename):
    "parse file, ``filename``."
    return parse_notes(file(filename).read())


def mergedict(A, B):
    "merge contents of A and B, taking B over A"
    c = {}
    for k in set(A).union(B):
        a = A.get(k, '')
        b = B.get(k, '')
        if a and b:
            #print 'merge error %s; %r %r' % (k, a, b)
            c[k] = b
        else:
            c[k] = a or b
    return c


def unicodify_dict(a):
    return {force_unicode(k): force_unicode(v).strip() for k,v in a.iteritems()}


def dictsubset(a, b):
    for k in a:
        if a[k] != '' and k in b and b[k] != a[k]:  # disagree on non-null value
            return False
    return True


_whitespace_cleanup = re.compile('[ ]*\n', re.MULTILINE)
def whitespace_cleanup(x):
    return _whitespace_cleanup.sub('\n', x)
