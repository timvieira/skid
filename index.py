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
from urllib2 import urlopen
from pdfutils.conversion import pdftotext
from iterextras import iterview


# globals
DIRECTORY = 'data~'
NAME = 'index'
CACHE = 'cache~'

def create():
    """ Create a new database. """
    print 'creating new database in directory %s' % DIRECTORY
    os.system('rm -rf %s' % DIRECTORY)
    os.mkdir(DIRECTORY)
    schema = Schema(path = ID(stored=True),
                    text = TEXT(stored=True),
                    tags = KEYWORD(stored=True))
    create_in(DIRECTORY, schema, NAME)


# create index if it doesn't exist
if not os.path.exists(DIRECTORY):
    create()

if not os.path.exists(CACHE):
    os.mkdir(CACHE)


ix = open_dir(DIRECTORY, NAME)


# TODO: do we want to convert a query with the term #my-tag to tags:my-tag?
def search(q):
    q = unicode(q.decode('utf8'))
    with ix.searcher() as searcher:
        qp = QueryParser('text', schema=ix.schema)
        qp.add_plugin(DateParserPlugin(free=True, basedate=datetime.now()))
        q = qp.parse(q)
        for hit in searcher.search(q):
            yield hit


def warn(x):
    print '[%s]' % yellow % 'warn', x




def import_document(location, tags):

    if isinstance(tags, basestring):
        tags = re.split(',\s*', tags)

    if os.path.exists(location):         # is this something on disk?
        tags.append('ondisk')
        filename = location              # leave the file where it is, no caching

    elif location.startswith('http'):    # cache links
        tags.append('link')

        # cache file
        filename = os.path.join(CACHE, secure_filename(location))

        if os.path.exists(filename):
            warn('file %s already cached at %s.' % (location, filename))

        content = urlopen(location).read()
        with file(filename, 'wb') as f:
            f.write(content)

        tags.append('cached')


    if filename.endswith('.pdf'):       # extract text from pdfs
        text = pdftotext(filename)

    else:
        with file(filename, 'r') as f:
            text = f.read()

        if filename.endswith('.html'):  # clean up html
            text = re.sub('<.*?>', '', content)

    # sha1 hash page

    with ix.writer() as w:
        w.add_document(path = unicode(location),
                       text = unicode(text.decode('utf8')),
                       tags = unicode(' '.join(tags)))


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

    _search = search
    def search(q):
        print
        print 'query:', q
        for hit in _search(q):
            print 'docnum:', hit.docnum
            print 'path:', hit['path']
#            print '\n'.join('%s: %s' % (k, hit[k]) for k in hit.fields() if k != 'parse')
            print
        print

    from automain import automain
    automain()
