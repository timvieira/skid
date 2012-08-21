import os
from datetime import datetime
from glob import glob

from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, KEYWORD, ID
from whoosh.qparser import QueryParser
from whoosh.qparser.dateparse import DateParserPlugin

from iterextras import iterview
from debug import ip

# globals
DIRECTORY = '/home/timv/.tags/index'
NAME = 'index'
from tags.pipeline import CACHE


def create():
    """ Create a new Whoosh index.. """
    print 'creating new index in directory %s' % DIRECTORY
    os.system('rm -rf %s' % DIRECTORY)
    os.mkdir(DIRECTORY)
    schema = Schema(source = ID(stored=True, unique=True),
                    title = TEXT(stored=True),
                    description = TEXT(stored=True),
                    text = TEXT(stored=True),
                    tags = KEYWORD(stored=True))
    create_in(DIRECTORY, schema, NAME)


def _search(q):
    q = unicode(q.decode('utf8'))
    ix = open_dir(DIRECTORY, NAME)
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


def drop():
    "Drop existing index."
    assert os.path.exists(DIRECTORY)
    os.system('rm -rf ' + DIRECTORY)


def build():
    "Rebuild index from scratch."

    assert not os.path.exists(DIRECTORY)

    # create index if it doesn't exist
    if not os.path.exists(DIRECTORY):
        create()

    # get handle to Whoosh index
    ix = open_dir(DIRECTORY, NAME)

    with ix.writer() as w:

        for d in iterview([d for d in glob(CACHE + '/*') if not d.endswith('.d')]):

            def get(attr):
                return unicode(file(d + '.d/' + attr).read().decode('utf8'))

            w.add_document(source = get('source'),
                           title = get('title'),
                           description = get('description'),
                           text = get('text'),
                           tags = get('tags'))


def shell():
    ix = open_dir(DIRECTORY, NAME)
    with ix.searcher() as searcher:
        with ix.writer() as writer:
            print 'use searcher and writer'
            ip()


def lexicon(field):
    """
    List lexicon entries from field. For example lexicon('tags') should return
    all know tags.
    """
    ix = open_dir(DIRECTORY, NAME)
    with ix.searcher() as s:
        return list(s.lexicon(field))


if __name__ == '__main__':
    from automain import automain
    automain()
