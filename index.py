"""
Index skid-marks to support efficient search over attributes including
full-text.
"""

import os
from datetime import datetime
from glob import glob

from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, KEYWORD, ID
from whoosh.qparser import QueryParser
from whoosh.qparser.dateparse import DateParserPlugin

from iterextras import iterview
from debug import ip

from skid.common import parse_notes
from skid.config import ROOT, CACHE

# globals
DIRECTORY = ROOT + '/index'
NAME = 'index'


def create():
    """ Create a new Whoosh index.. """
    print 'creating new index in directory %s' % DIRECTORY
    os.system('rm -rf %s' % DIRECTORY)
    os.mkdir(DIRECTORY)
    schema = Schema(source = ID(stored=True, unique=True),
                    cached = ID(stored=True, unique=True),
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
    """
    Search skid-marks for particular attributes.
    """
    print
    print 'query:', q
    for hit in _search(q):
        print 'docnum:', hit.docnum
        #fields = list(hit.fields())
        fields = ['title', 'cached', 'source', 'tags']
        for k in fields:
            val = hit[k].strip()
            if val and k != 'text':
                if k == 'cached':
                    val = 'file://' + val
                print '\033[31m%s\033[0m: %s' % (k, val.replace('\n', ' '))
        #snippet(hit['cached'] + '.d/data/text', q)
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

            text = file(d + '.d/data/text').read().decode('utf8')
            meta = parse_notes(file(d + '.d/notes.org').read())

            w.add_document(source = meta['source'],
                           title = meta['title'],
                           cached = unicode(d),
                           description = meta['description'],
                           text = text,
                           tags = meta['tags'])


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
