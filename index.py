"""
TODO:

 - urls with a glob in them get expanded..
   e.g.  http://web.archive.org/web/*/http://www.srcf.ucam.org/~hmw26/join-the-dots/

 - convert a query with the term #my-tag to tags:my-tag

 - update entry (instead of ignore with warning) existing paths in database

 - should we redownload if file is already cached?

"""

import os
from datetime import datetime
from glob import glob

from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, KEYWORD, ID

from whoosh.qparser import QueryParser
from whoosh.qparser.dateparse import DateParserPlugin

from debug import ip
import re
from terminal import yellow, red, blue, green
from fsutils import secure_filename, mkdir
from pdfutils.conversion import pdftotext
from iterextras import iterview
from web.download import download

# globals
DIRECTORY = 'data~'
NAME = 'index'
CACHE = 'cache~'

def create():
    """ Create a new Whoosh index.. """
    print 'creating new database in directory %s' % DIRECTORY
    os.system('rm -rf %s' % DIRECTORY)
    os.mkdir(DIRECTORY)
    schema = Schema(path = ID(stored=True, unique=True),
                    title = TEXT(stored=True),
                    description = TEXT(stored=True),
                    text = TEXT(stored=True),
                    tags = KEYWORD(stored=True))
    create_in(DIRECTORY, schema, NAME)


# create index if it doesn't exist
if not os.path.exists(DIRECTORY):
    create()

if not os.path.exists(CACHE):
    os.mkdir(CACHE)

# handle to Whoosh index
ix = open_dir(DIRECTORY, NAME)

def _search(q):
    q = unicode(q.decode('utf8'))
    with ix.searcher() as searcher:
        qp = QueryParser('text', schema=ix.schema)
        qp.add_plugin(DateParserPlugin(free=True, basedate=datetime.now()))
        q = qp.parse(q)
        for hit in searcher.search(q):
            yield hit

def search(q):
    print
    print 'query:', q
    for hit in _search(q):
        print 'docnum:', hit.docnum
        print '\n'.join('%s: %s' % (k, hit[k]) for k in hit.fields() if k != 'text')
        print
    print


def warn(x):
    print '[%s]' % yellow % 'warn', x


from text.utils import htmltotext, remove_ligatures, force_unicode

def plaintext(filename):

    ext = os.path.splitext(filename)[1][1:]  # remove the dot

    if ext == 'pdf':
        # extract text from pdfs
        text = pdftotext(filename, verbose=True, usecached=True)

#    elif ext in ('', 'org', 'txt', 'html', 'htm', 'md', 'tex', 'markdown', 'rst'):

    else:

        with file(filename, 'r') as f:
            text = f.read()

        # strip tags and xml entities from html
#        if ext in ('.html', '.htm'):
        text = force_unicode(text)

        text = htmltotext(text)

#    else:
#        text = '-*-missing-*-'

    # TODO: post processing to remove junk like ligatures

    text = remove_ligatures(text)

    return text


def cache_url(url):

    try:
        cached = download(url, tries=3, usecache=True, cachedir=CACHE)
        if not cached:
            print 'Failed to download %s.' % url
            return

    except KeyboardInterrupt:
        return

    else:
        return cached


def cache_document(location):
    "Cache a document, return filename of the cached file."

    if location.startswith('http'):    # cache links
        return cache_url(location)

    elif os.path.exists(location):   # is this something on disk?

        # TODO: make symlink and .d directory inside cache. What if the .d
        # directory exists near the file already?
        return location

    else:
        assert False


def import_document(location, tags, title='', description=''):

    print blue % 'adding %s' % location

    if isinstance(tags, basestring):
        tags = tags.split()


    # classify
    if os.path.exists(location):         # is this something on disk?
        tags.append('$local')
    elif location.startswith('http'):    # cache links
        tags.append('$url')


    cached = cache_document(location)

    print cached

    if cached:
        tags.append('$cached')
    else:
        tags.append('$failed-to-cache')

    print 'dir:', cached + '.d'
    mkdir(cached + '.d')

    def meta(name, content):
        with file(cached + '.d/' + name, 'wb') as f:
            if not isinstance(content, basestring):
                content = '\n'.join(content)
            content = force_unicode(content)
            content = content.encode('utf8')
            f.write(content)
            f.write('\n')    # new line at end of file

    if cached:
        text = plaintext(cached)
        meta('text', text)
        meta('tags', tags)
        meta('title', title)
        meta('description', description)
        meta('location', location)


def index_document(cached):
    assert os.path.exists(cached) and os.path.exists(cached + '.d')

    with ix.searcher() as searcher:
        results = searcher.find('path', unicode(cached + '.d/location'))
        if len(results) != 0:
            print results
            warn('document already added.')
            return

    raise NotImplementedError('open up the files...')

#    with ix.writer() as w:
#        w.add_document(path = unicode(location),
#                       title = unicode(title or location),
#                       description = unicode(description or '-*- missing -*-'),
#                       text = text,
#                       tags = unicode(' '.join(tags)))


def add_delicious():
    from BeautifulSoup import BeautifulSoup
    with file('delicious_timvieira.xml') as f:
        soup = BeautifulSoup(f)
        for post in iterview(soup.findAll('post')):
            print
            import_document(location = post['href'],
                            tags = post['tag'],
                            title = post['description'],
                            description = post['extended'])

def add_pdfs():
    for filename in iterview(glob('/home/timv/projects/document-explorer/data/*.pdf')):
        import_document(filename, [])

def shell():
    with ix.searcher() as searcher:
        with ix.writer() as writer:
            print 'use searcher and writer'
            ip()

def lexicon(field):
    with ix.searcher() as s:
        return list(s.lexicon(field))


if __name__ == '__main__':
    from automain import automain
    automain()
