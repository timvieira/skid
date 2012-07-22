"""
TODO:

 - urls with a glob in them get expanded..
   e.g.  http://web.archive.org/web/*/http://www.srcf.ucam.org/~hmw26/join-the-dots/

 - convert a query with the term #my-tag to tags:my-tag

 - update entry (instead of ignore with warning) existing paths in database
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
from fsutils import secure_filename
from urllib2 import urlopen, URLError
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
        print 'title:', hit['title']
        print 'path:', hit['path']
        print 'tags:', hit['tags']
        #print '\n'.join('%s: %s' % (k, hit[k]) for k in hit.fields() if k != 'parse')
        print
    print


def warn(x):
    print '[%s]' % yellow % 'warn', x


def import_document(location, tags, title='', description=''):

    print blue % 'adding %s' % location

    if isinstance(tags, basestring):
        tags = tags.split()

    # handle directories os.path.isdir
    # expand ~
    # source code: python, java, scala
    # plain text

    with ix.searcher() as searcher:
        results = searcher.find('path', unicode(location))
        if len(results) != 0:
            print results
            warn('document already added.')
            return

    if os.path.exists(location):         # is this something on disk?
        tags.append('$local')
        filename = location              # leave the file where it is, no caching

    elif location.startswith('http'):    # cache links
        tags.append('$url')

        # cache file
        filename = os.path.join(CACHE, secure_filename(location))

        if os.path.exists(filename):
            warn('file %s already cached at %s.' % (location, filename))

        try:
            content = download(location, tries=3, usecache=True, cachedir='cache~')
            with file(filename, 'wb') as f:
                f.write(content)
        except (KeyboardInterrupt, URLError):
            tags.append('$failed-to-cache')
        else:
            tags.append('$cached')

    if filename.endswith('.pdf'):       # extract text from pdfs
        text = pdftotext(filename)

    else:
        if os.path.exists(filename):

            with file(filename, 'r') as f:
                text = f.read()

            if filename.endswith('.html'):  # clean up html
                text = re.sub('<.*?>', '', content)

        else:
            text = '-*- missing -*-'

    # sha1 hash of text or content

    try:
        text = unicode(text.decode('utf8'))
    except:
        text = unicode(text.decode('latin1'))

    with ix.writer() as w:
        w.add_document(path = unicode(location),
                       title = unicode(title or location),
                       description = unicode(description or '-*- missing -*-'),
                       text = text,
                       tags = unicode(' '.join(tags)))


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
