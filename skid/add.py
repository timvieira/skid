#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Add document to skid (cache document, extract text, create metadata files).
"""
import re, os, subprocess
from path import path
from datetime import datetime

from skid.config import CACHE
from skid.pdfhacks import pdftotext, extract_title

from arsenal.terminal import blue
from arsenal.web.download import download
from arsenal.text.utils import htmltotext, force_unicode, remove_ligatures
from arsenal.fsutils import secure_filename


class SkidError(Exception):
    pass


def uni(x):
    if isinstance(x, list):
        return map(uni, x)
    assert isinstance(x, basestring), x
    return force_unicode(x)

def unicodify_dict(a):
    return {uni(k): uni(v) for k,v in a.iteritems()}


# TODO: use wget instead, it's more robust and has more bells and
# whistles.. e.g. handling redirects, ftp, timeouts, and all sorts of silly
# things that happen when downloading a file.
def cache_url(url):
    """
    Download url, write contents to file. Return filename of contents, None on
    failure to download.
    """
    cached = CACHE / secure_filename(url)

    assert not cached.exists(), 'File %s already exists.' % cached

    # TODO: we should tell download where to store stuff explicitly... right now
    # we just both have the same convention.
    if not download(url, timeout=60, usecache=False, cached=cached):
        raise Exception('Failed to download %s.' % url)

    return cached


def cache_document(src):
    "Cache a document, return filename of the cached file."

    # TODO: use staging area

    src = path(src)

    if src.startswith('https:') or src.startswith('http:') or src.startswith('ftp:'):    # cache links
        return cache_url(src)

    elif src.exists():   # is this something on disk?

        dest = CACHE / src.basename()

        if dest.exists():
            # TODO: check if hash is the same. Suggest update methods or
            # renaming the file (possibly automatically, e.g. via hash).
            raise Exception('File %r already exists' % dest)

        src.copy2(dest)

        print 'copy:', src, '->', dest

        return dest

    raise SkidError("cache_document doesn't know what to do with source %s" % src)


# TODO:
#
# - "atomically" write directory to avoid issues with failures. Do this by
#   staging. It will also help with clobbering existing stuff, unfinished or
#   aborted imports.
#
# - If it's a pdf we should try to get a bibtex entry for it.
#
def document(source, interactive=True):
    """
    Import document from ``source``. Procedure will download/cache the file,
    create a directory to store metadta.
    """

    assert ' ' not in source

    source = path(source)

    print blue % 'adding %s' % source

    # store the absolute path for local files.
    if source.exists():
        source = source.abspath()

    cached = cache_document(source)

    print cached

    d = Document(cached)

    d.write_hash()
    d.extract_plaintext()

    meta = {
        'title': d.extract_title(),
        'author': '',
        'year': '',
        'tags': '',
        'notes': '',
        'source': source,
        'cached': cached,
    }

    d.store('notes.org', d.note_template(meta))

    d.store('data/date-added', str(datetime.now()))

    if interactive:
        d.edit_notes()

    print "Don't forget to 'skid update'"

    return d


# TODO: everything pertaining to Document should appear here probably including
# methods to: find most-similar documents, insert/delete/update index

# XXX: attributes fall into categories
#  1. backed by a file
#  2. extracted from notes
#  3. derived (e.g. text extraction)
class Document(object):
    """

    Notes:

     - Creating an instance of Document has side effects: creates `{cached}.d`
       directory if it doesn't exist.

       TODO: add option to avoid this?

    """

    def __init__(self, cached):

        if cached.startswith('file://'):
            cached = cached[7:]

        self.cached = path(cached).expand().abspath()
        assert self.cached.exists(), 'File %r does not exist' % self.cached
        self.d = self.cached + '.d'

        if not self.d.exists():
            self.d.mkdir()
            (self.d / 'data').mkdir()

    @property
    def added(self):
        x = (self.d / 'data' / 'date-added').text().strip()
        try:
            return datetime.strptime(x, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            return datetime.strptime(x, '%Y-%m-%d %H:%M:%S')

    @property
    def modified(self):
        return datetime.fromtimestamp(self.d.mtime)

    def __repr__(self):
        return 'Document("%s")' % self.cached

    def edit_notes(self):
        subprocess.call(os.environ.get('EDITOR', 'nano').split() + [self.d / 'notes.org'])

    def store(self, name, content, overwrite=False):
        t = self.d / name
        assert overwrite or not t.exists(), name + ' already exists!'
        with file(t, 'wb') as f:
            content = force_unicode(content)
            content = content.encode('utf8')
            f.write(content)
            f.write('\n')    # new line at end of file
        return content

    def write_hash(self):
        return self.store('data/hash', self.cached.read_hexhash('sha1'), overwrite=True)

    def hash(self):
        return unicode((self.d / 'data' / 'hash').text().decode('utf8'))

    def extract_title(self):

        if self.cached.endswith('.pdf'):
            return extract_title(self.cached)

        else:
            # assume it's HTML
            x = re.findall('<title>(.*?)</title>', self.cached.text(), flags=re.I)
            if x:
                return x[0].strip()  # take the first title
            else:
                return ''   # TODO: maybe take first line of the file?

    def text(self):
        return (self.d / 'data' / 'text').text().decode('utf8')

    def extract_plaintext(self):
        "Extract plaintext from filename. Returns text, might cache."

        if self.cached.endswith('.pdf'):
            # extract text from pdfs
            text = pdftotext(self.cached, output=self.d / 'data' / 'pdftotext.txt',
                             verbose=True, usecached=True)

        else:
            text = self.cached.text()
            text = force_unicode(text)
            text = htmltotext(text)      # clean up html

        text = remove_ligatures(text)

        return self.store('data/text', text, overwrite=True)

    def note_template(self, x):
        others = set(x) - set('title author year source cached tags notes'.split())
        attrs = u'\n'.join((u':%s: %s' % (k, x[k])).strip() for k in others).strip()
        if attrs:
            attrs += '\n'
        newdata = TEMPLATE.format(attrs=attrs, **x)
        return force_unicode(newdata).encode('utf8')

    # TODO: do not like...
    def note_content(self):
        f = self.d / 'notes.org'
        if not f.exists():
            raise SkidError('Note file missing for %r.' % self)
        return f.text().decode('latin1')

    # TODO: use a lazy-loaded attribute?
    # TODO: better markup language? or better org-mode markup.
    def parse_notes(self):
        "Extract metadata from notes.org."

        content = self.note_content()

        # timv: merge multiple values for same key?
        metadata = re.findall('^(?:\#\+?|:)([^:\s]+):[ ]*([^\n]*?)\s*$',
                              content, re.MULTILINE)

        x = {'title': '', 'author': '', 'year': '',
             'source': '', 'cached': '', 'tags': ''}
        for k, v in metadata:
            v = v.strip()
            if k in ('cached','source'):
                # remove org-mode's link markup
                v = re.sub('^\[\[(.*?)\]\]$', r'\1', v)
                v = re.sub('(file://)', '', v)

            if k in ('link',):

                orglink = '\[\[(' + '[^\[\]]*?' + ')\]\[%s\]\]'

                source = re.findall(orglink % 'source', v)
                cached = re.findall(orglink % 'cached', v)

                if len(source) == 1:
                    x['source'] = source[0]

                if len(cached) == 1:
                    x['cached'] = cached[0]

                continue

            x[k] = v

        # split authors and tags
        x['tags'] = x['tags'].strip().split()
        x['author'] = filter(None, [a.strip() for a in x['author'].strip().split(';')])

        [d] = re.findall('\n([^:#][\w\W]*$|$)', content)
        x['notes'] = d.strip()

        return unicodify_dict(x)

    def similar(self, limit, numterms=40, fieldname='text'):
        "Most similar results to document."
        from skid import index
        ix = index.open_dir(index.DIRECTORY, index.NAME)
        with ix.searcher() as searcher:
            results = searcher.find('cached', unicode(self.cached))
            result = results[0]
            for hit in result.more_like_this(top=limit, numterms=numterms, fieldname=fieldname):
                yield hit


TEMPLATE = u"""\
#+title: {title}
:author: {author}
:year:   {year}
:link:   [[{source}][source]], [[{cached}][cached]]
:tags:   {tags}
{attrs}
{notes}
""".encode('utf8')


if __name__ == '__main__':
    # use test environment
    from skid import config
    ROOT = config.ROOT = path('~/.skid-test').expand()
    CACHE = config.CACHE = ROOT / 'marks'

    os.system('rm -rf /home/timv/.skid-test/marks/POPL2013-abstract.pdf*')

    test_src = '/home/timv/Desktop/POPL2013-abstract.pdf'
    test_cached = CACHE / 'POPL2013-abstract.pdf'
    test_doc = document(test_src, interactive=False)

    print test_doc

    test = Document(test_cached)
#    from arsenal.debug import ip; ip()
    from pprint import pprint
    pprint(test.parse_notes())
