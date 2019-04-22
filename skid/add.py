#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Add document to skid (cache document, extract text, create metadata files).
"""
import re, os, socket, subprocess
from path import Path
from datetime import datetime

from skid.config import CACHE
from skid.pdfhacks import pdftotext, extract_title
from skid.utils.text import htmltotext, remove_ligatures

from arsenal.terminal import colors
from arsenal.download import download
from arsenal.fsutils import secure_filename
from arsenal.humanreadable import str2bool


class SkidError(Exception):
    pass


class SkidDownloadError(SkidError):
    pass


class SkidFileExists(SkidError):
    def __init__(self, filename):
        self.filename = filename
        super(SkidFileExists,self).__init__('file %r already exists' % filename)


def uni(x):
    if isinstance(x, list):
        return list(map(uni, x))
    assert isinstance(x, str), x
    return x

def unicodify_dict(a):
    return {uni(k): uni(v) for k,v in list(a.items())}


from chardet.universaldetector import UniversalDetector
def robust_read(filename, verbose=0):
    detector = UniversalDetector()
    for line in open(filename, mode='rb'):
        detector.feed(line)
        if detector.done:
            break
    detector.close()
    if verbose:
        print('encoding:', detector.result)
    encoding = detector.result['encoding'] or 'utf8'
    with open(filename, mode='r', encoding=encoding, errors='ignore') as f:
        return f.read()


from io import StringIO
def robust_read_string(x, verbose=0):
    detector = UniversalDetector()
    #for line in StringIO(x):
    detector.feed(x)
    #if detector.done:
    #    break
    detector.close()
    if verbose:
        print('encoding:', detector.result)
    encoding = detector.result['encoding'] or 'utf8'
    return x.decode(encoding, 'replace').encode('utf8')


# TODO: use wget instead, it's more robust and has more bells and
# whistles.. e.g. handling redirects, ftp, timeouts, and all sorts of silly
# things that happen when downloading a file.
def cache_url(url, dest):
    """
    Download url, write contents to file. Return filename of contents, None on
    failure to download.
    """

    # TODO: we should tell download where to store stuff explicitly... right now
    # we just both have the same convention.
    if not download(url, timeout=60, usecache=False, cached=dest):
        raise SkidDownloadError(url)


def is_url(src):
    return src.startswith('https://') or src.startswith('http://') or src.startswith('ftp://')


def cache_document(src, dest=None):
    "Cache a document, return filename of the dest file."

    # TODO: use a staging area in case something breaks in the middle of adding.
    src = Path(src)

    if dest is None:
        # Find a reasonable filename if dest isn't specified
        if is_url(src):
            dest = CACHE / secure_filename(src)
        else:
            dest = CACHE / src.basename()
    else:
        dest = CACHE / dest

    if dest.exists():
        # TODO: Suggest update methods or renaming the file
        raise SkidFileExists(dest)

    if is_url(src):
        cache_url(src, dest)

    elif src.exists():   # is this something on disk?
        src.copy2(dest)
        print('copy:', src, '->', dest)

    else:
        raise SkidError("cache_document doesn't know what to do with source %r\n"
                        "Trying to add a nonexistent file?" % str(src))

    return dest

# TODO:
#
# - "atomically" write directory to avoid issues with failures. Do this by
#   staging. It will also help with clobbering existing stuff, unfinished or
#   aborted imports.
#
# - If it's a pdf we should try to get a bibtex entry for it.
#
def document(source, dest=None, interactive=True):
    """
    Import document from ``source``. Procedure will download/cache the file,
    create a directory to store metadta.
    """

    assert ' ' not in source

    if dest is not None:
        assert re.match('^[a-zA-Z0-9\-_.]+$', dest), \
            '%r is not a valid name for a skid document.' % dest
        dest = Path(dest)

    source = Path(source)

    print(colors.blue % 'adding %s' % source)

    # store the absolute path for local files.
    if source.exists():
        source = source.abspath()

    exists = False
    try:
        cached = cache_document(source, dest=dest)

    except SkidFileExists as e:
        print('[%s] document already cached. using existing notes.' % colors.yellow % 'warn')
        cached = e.filename
        exists = True

    except SkidDownloadError as e:
        print('[%s] Failed to download (%s).' % (colors.red % 'error', e))
        return

    d = Document(cached)

    if not exists:
        new_document(d, source, cached)

    if interactive:
        d.edit_notes()

    print("Don't forget to 'skid update'")

    return d


def new_document(d, source, cached):

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

    if meta['title']:
        bib = {}
        try:
            bib = gscholar_bib(title=meta['title']) or {}
        except Exception as e:
            raise e
#        except KeyError: # TODO: fix encoding errors
#            pass
#        except socket.error as e:
#            print(colors.yellow % '[gscholar] error %s' % e)
        else:
            # Ask user if the bib entry retrieved looks any good.
            if bib.get('title'):

                #xx = bib.get('title').lower()
                #yy = meta['title'].lower()

                #from arsenal.nlp.similarity.levenstein import damerau_levenshtein as edit_distance
                #dist = edit_distance(xx, yy)
                #sim = 1 - dist / max(len(xx), len(yy))
                #print colors.yellow % 'title similarity: %.2f%%' % (sim)

                msg = 'Initialize note file with above bib info?'
                #if sim < 0.75:
                #    print msg + ' [y/%s]' % colors.red % 'N'
                #    print '-> Similarity too low, will not use.'
                #else:
                if 1:
                    while 1:
                        try:
                            s = input(msg + ' [y/N] ').strip()
                            if not s:
                                bib = {}
                                break
                            s = str2bool(s)
                            if not s:
                                bib = {}
                            break
                        except ValueError:
                            pass


            if bib:
                meta.update(bib)

    # TODO: gross hack.
    #meta = {k: robust_read_string(v) for k,v in meta.items()}
    meta = {k: (v or '') for k,v in list(meta.items())}

    d.store('notes.org', d.note_template(meta))
    d.store('data/date-added', str(datetime.now()))


def gscholar_bib(title):
    #print('[WARNING] Google scholar search is currently disabled.')
    #return # CURRENTLY DISABLED.

    # perform a Google scholar search based on the title.
    import urllib.request, urllib.error, urllib.parse
    from skid.utils import gscholar
    import pybtex
    from pybtex.database.input import bibtex
    from nameparser import HumanName
    #import latexcodec

    print(colors.magenta % 'Google scholar results for title:')
    try:
        results = gscholar.query(title, allresults=False)
    except (KeyboardInterrupt, urllib.error.URLError) as e:
        results = []
        print('[%s] %s' % (colors.yellow % 'warn', 'Google scholar search failed (error: %s)' % e))
        raise e

    for x in results:
        print(x)

        x = x.decode('ascii', errors='ignore')

        try:
            b = bibtex.Parser().parse_stream(StringIO(x))
        except pybtex.scanner.TokenRequired as e:
            print('failed to parse bibtex with error:', e)
            return

        [(_,e)] = list(b.entries.items())

        #print colors.yellow % (dict(e.fields),)
        title = e.fields['title']
        year = e.fields.get('year', '')
        author = ' ; '.join(str(HumanName(x)) for x in re.split(r'\band\b', e.fields['author']))

        #title = title.decode('latex')
        #author = author.decode('latex').replace('{','').replace('}','')

        print(title)
        print(year)
        print(author)
        print()

        return {'title': title,
                'year': year,
                'author': author}



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

        self.cached = Path(cached).expand().abspath()
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
        with open(t, 'wb') as f:
            if hasattr(content, 'encode'):
                f.write(content.encode('utf-8'))
            else:
                f.write(content)
            f.write(b'\n')    # new line at end of file
        return content

    def write_hash(self):
        return self.store('data/hash', self.cached.read_hexhash('sha1'), overwrite=True)

    def hash(self):
        return str((self.d / 'data' / 'hash').text())

    def extract_title(self):

        if self.cached.endswith('.pdf'):
            return extract_title(self.cached)

        else:
            # assume it's HTML
            x = re.findall('<title>(.*?)</title>', robust_read(self.cached), flags=re.I)
            if x:
                return x[0].strip()  # take the first title
            else:
                return ''   # TODO: maybe take first line of the file?

    def text(self):
        return robust_read(self.d / 'data' / 'text')

    def extract_plaintext(self):
        "Extract plaintext from filename. Returns text, might cache."

        if self.cached.endswith('.pdf'):
            # extract text from pdfs
            text = pdftotext(self.cached, output=self.d / 'data' / 'pdftotext.txt',
                             verbose=True, usecached=True)

        else:
            text = robust_read(self.cached)
            text = htmltotext(text)      # clean up html

        text = remove_ligatures(text)

        return self.store('data/text', text, overwrite=True)

    def note_template(self, x):
        x = unicodify_dict(x)
        others = set(x) - set('title author year source cached tags notes'.split())
        attrs = '\n'.join((':%s: %s' % (k, x[k])).strip() for k in others).strip()
        if attrs:
            attrs += '\n'
        newdata = TEMPLATE.format(attrs=attrs, **x)
        return newdata.encode('utf8')

    def note_content(self):
        filename = self.d / 'notes.org'
        if not filename.exists():
            raise SkidError('Note file missing for %r.' % self)

        # notes should always be utf-8...
        return open(filename).read().encode('utf8','ignore').decode('utf8','ignore')
        #return robust_read(filename)

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
        x['author'] = [_f for _f in [a.strip() for a in x['author'].strip().split(';')] if _f]

        [d] = re.findall('\n([^:#][\w\W]*$|$)', content)
        x['notes'] = d.strip()

        return unicodify_dict(x)

    def similar(self, limit, numterms=40, fieldname='text'):
        "Most similar results to document."
        from skid import index
        ix = index.open_dir(index.DIRECTORY, index.NAME)
        with ix.searcher() as searcher:
            results = searcher.find('cached', str(self.cached))
            result = results[0]
            for hit in result.more_like_this(top=limit, numterms=numterms, fieldname=fieldname):
                yield hit


TEMPLATE = """\
#+title: {title}
:author: {author}
:year:   {year}
:link:   [[{source}][source]], [[{cached}][cached]]
:tags:   {tags}
{attrs}
{notes}
"""


if __name__ == '__main__':
    # use test environment
    from skid import config
    from pprint import pprint

    ROOT = config.ROOT = Path('/tmp/skid-test').expand()
    CACHE = config.CACHE = ROOT / 'marks'

    os.system('rm -rf /tmp/skid-test/marks/POPL2013-abstract.pdf*')

    test_src = '/home/timv/Desktop/POPL2013-abstract.pdf'
    test_cached = CACHE / 'POPL2013-abstract.pdf'
    test_doc = document(test_src, interactive=False)

    print(test_doc)

    test = Document(test_cached)
    pprint(test.parse_notes())
