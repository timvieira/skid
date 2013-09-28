#!/usr/bin/env python
"""
Cute script which takes a bibtex file and renders it in various ways with LaTeX,
then extracts the text with pdftotext. (the noisy channel: I wanted to send you
a nice bibtex file along with my pdfs, but some body corrupted it into LaTeX and
then the pdf standard made it difficult to pull the text out! Doubly corrupted.)
"""

import re, os, sys
from StringIO import StringIO
from os import path
from hashlib import sha1
from subprocess import Popen, PIPE
from collections import defaultdict

# github.com/timvieira/python-extras
from arsenal.fsutils import cd
from arsenal.text.utils import force_unicode
from arsenal.iterextras import take
from arsenal.terminal import green, blue, red, yellow

from skid.pdfhacks.conversion import pdftotext

# pybtex - http://packages.python.org/pybtex/manual.html
from pybtex.database.input import bibtex
from pybtex.exceptions import PybtexError


def system(cmd):
    return Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE).wait()

latex_template = r"""
\documentclass[11pt]{article}
\begin{document}
\nocite{*}
\bibliography{%s}{}
\bibliographystyle{%s}
\end{document}
"""

def compilepdf(f):
    return system('pdflatex -halt-on-error {f}'
                  ' && bibtex {f}'
                  ' && pdflatex -halt-on-error {f}'
                  ' && pdflatex -halt-on-error {f}'.format(f=f))

# http://www.tex.ac.uk/tex-archive/help/Catalogue/alpha.html
# http://www.cs.stir.ac.uk/~kjt/software/latex/showbst.html
#STYLES = ['plain']
STYLES = """abbrv abstract acm alpha amsalpha amsplain annotate annotation
 apalike apalike2 cell is-abbrv is-alpha is-plain is-unsrt jmb nar plain unsrt
 phcpc phiaea plainyr""".split()

def bib2txt(bib, style='plain', workingdir='tmp/bibhacks'):
    """Given a BibTeX entries generate a plaintext reference section."""
    prefix = sha1(bib).hexdigest()
    with cd(workingdir):
        with file(prefix + '.bib', 'wb') as f:
            f.write(bib)
        with file(prefix + '.tex', 'wb') as f:
            f.write(latex_template % (prefix, style))
        compilepdf(prefix)
        if path.exists(prefix + '.pdf'):
            return pdftotext('%s.pdf' % prefix,
                             output='%s.plain.txt' % prefix,
                             usecached=False)


def stacked(x, B, E):
    """
    >>> x = '( (abc [1 2 3] ) () )'
    >>> stacked(x, '(', ')') == len(x) - 1
    True
    """
    assert x[0] == B
    stack = [x[0]]
    N = len(x)
    i = 0
    while stack:
        i += 1
        if i >= N:
            raise AssertionError
        c = x[i]
        if c == B:
            stack.append(c)
        elif c == E:
            if stack[-1] == B:
                stack.pop(-1)  # remove last
            else:
                stack.append(c)
        else:
            pass
    return i


def find_entries(filename):
    with file(filename, 'r') as f:
        c = f.read()

    open2close = {'(': ')', '{': '}'}
    BEGIN = re.compile('^@([a-zA-Z]+)([{(])', re.MULTILINE)

    for begining in BEGIN.finditer(c):

        _, beginthing = begining.groups()
        entrybodybegin = begining.end() - 1
        entryend = stacked(c[entrybodybegin:], beginthing, open2close[beginthing])

        raw = c[begining.start():entrybodybegin+entryend+1]

        try:
            yield Entry(raw)
        except PybtexError as e:
            if 'undefined macro' not in str(e):
                print e


fields = defaultdict(list)

# XXX: Person(first, middle, prelast", last, lineage)

class Entry(object):
    """
    BibTeX Entry
    """
    def __init__(self, raw):
        self._raw = raw
        self.raw = force_unicode(raw.strip())
        self.styles = {}

        bibliography = bibtex.Parser().parse_stream(StringIO(self.raw))
        entries = bibliography.entries
        assert len(entries) == 1, 'Entry is supposed to represent only one BibTex entry.'

        self.key, self.entry = entries.items()[0]
        self.fields = self.entry.fields

        for role, people in self.entry.persons.items():
            self.fields[role] = people

        assert len(self.entry.persons) <= 2, 'ERROR: too people.'

        for k in self.fields:
            fields[k].append(self)

    def pprint(self):
        print green % '<BibTeX key="%s">' % self.key

        for k, v in self.fields.items():
            print '    %s => %s' % (blue % k, v)

        for style in STYLES:
            mention = self.render(style).strip()
            print mention

        print green % '</BibTeX>'

    def render(self, style='plain'):
        if style not in self.styles:
            x = self.styles[style] = bib2txt(self.raw, style=style)
        x = self.styles[style]
        return x

def main(f):
    os.system('mkdir -p tmp/bibhacks')
    for entry in take(10, find_entries(f)):
        entry.pprint()
        print

if __name__ == '__main__':
    if len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        print 'usage %s <something.bib>' % sys.argv[0]
