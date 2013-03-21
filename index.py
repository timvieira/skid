"""
Index skid-marks to support efficient search over attributes including
full-text.
"""

# TODO: "clean-up script" which find files in cache which might have been
# deleted manually. Currently, the way to do this is to drop and rebuild the
# entire index

import re, os
from datetime import datetime

from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, KEYWORD, ID, DATETIME
from whoosh.qparser import QueryParser, MultifieldParser
from whoosh.analysis import StandardAnalyzer

from skid.config import ROOT, CACHE
from skid.add import Document

# globals
DIRECTORY = ROOT + '/index'
NAME = 'index'

# TODO: date added
def create():
    """ Create a new Whoosh index.. """
    print 'creating new index in directory %s' % DIRECTORY
    os.system('rm -rf %s' % DIRECTORY)
    os.mkdir(DIRECTORY)
    schema = Schema(source = ID(stored=True, unique=True),
                    cached = ID(stored=True, unique=True),
                    hash = ID(stored=True, unique=True),
                    title = TEXT(stored=True),
                    author = TEXT(stored=True),
                    year = TEXT(stored=True),
                    notes = TEXT(stored=True),
                    text = TEXT(stored=True),
                    tags = KEYWORD(stored=True),
                    mtime = DATETIME(stored=True))
    create_in(DIRECTORY, schema, NAME)


def search(q, limit=10):
    q = unicode(q.decode('utf8'))
    ix = open_dir(DIRECTORY, NAME)
    with ix.searcher() as searcher:
        qp = MultifieldParser(fieldnames=['title', 'author', 'tags', 'notes', 'text'],
                              fieldboosts={'title': 5,
                                           'author': 5,
                                           'tags': 5,
                                           'notes': 2,
                                           'text': 1},
                              schema=ix.schema)
        # pass query thru standard analyzer or else Whoosh will choke on stopwords
#        q = u' '.join(tk.text for tk in StandardAnalyzer()(q))   # this fails on attributes, e.g. "author:vieira"
#        from arsenal.debug import ip; ip()

        # expect user to use 'AND' and 'OR' for conjunctive/disjunctive queries
        q = re.sub(r'\b(and|or)\b', '', q) # remove 'and' and 'or'

        q = qp.parse(q)
        for hit in searcher.search(q, limit=limit):
            yield hit


#def search2(q, limit=10):
#    q = unicode(q.decode('utf8'))
#    ix = open_dir(DIRECTORY, NAME)
#    with ix.searcher() as searcher:
#        qp = QueryParser('text', schema=ix.schema)
#        q = qp.parse(q)
#        for hit in searcher.search(q, limit=limit):
#            yield hit


#def correct(qstr):
#    qstr = unicode(qstr.decode('utf8'))
#    ix = open_dir(DIRECTORY, NAME)
#    with ix.searcher() as searcher:
#        qp = QueryParser('text', schema=ix.schema)
#        q = qp.parse(qstr)
#        return searcher.correct_query(q, qstr, allfields=True)


def drop():
    "Drop existing index."
    assert DIRECTORY.exists()
    os.system('rm -rf ' + DIRECTORY)
    print 'dropped index', DIRECTORY


def delete(cached):
    "Remove file from index."
    try:
        ix = open_dir(DIRECTORY, NAME)
        with ix.searcher() as searcher, ix.writer() as w:
            qp = QueryParser(u'cached', ix.schema)
            q = qp.parse(unicode(cached))
            # should only get one hit.
            [hit] = searcher.search(q)
            w.delete_document(hit.docnum)
    except ValueError:
        print 'Cached file %r not found in index.' % cached


def update():
    "Rebuild index from scratch."

    # create index if it doesn't exist
    if not DIRECTORY.exists():
        create()

    # get handle to Whoosh index
    ix = open_dir(DIRECTORY, NAME)

    # TODO: quicker ways to update modified files: sort files by mtime; stop
    # updating at the first unchanged file.
    with ix.writer() as w, ix.searcher() as searcher:

        for cached in CACHE.files():

            d = Document(cached)

            # mtime of directory, not the cached file
            mtime = datetime.fromtimestamp(d.d.mtime)

            # lookup document mtime in the index; don't add or extract info if
            # you don't need it.
            result = searcher.find('cached', unicode(cached))

            if not result:
                print '[INFO] new document', cached

            else:
                assert len(result) == 1, 'cached should be unique.'
                result = result[0]
                if mtime <= result['mtime']:   # skip if document hasn't changed
                    continue

                print '[INFO] update to existing document:', cached

            text = d.text()

            meta = d.parse_notes()

            with file(cached + '.d/data/hash') as h:
                h = unicode(h.read().decode('utf8'))

            w.update_document(source = meta['source'],
                              cached = unicode(cached),
                              hash = h,
                              title = meta['title'],
                              author = meta.get('author', u''),
                              year = meta.get('year', u''),
                              notes = meta['notes'],
                              text = text,
                              mtime = mtime,
                              tags = meta['tags'])


def lexicon(field):
    """
    List lexicon entries from field. For example lexicon('tags') should return
    all know tags.
    """
    ix = open_dir(DIRECTORY, NAME)
    with ix.searcher() as s:
        return list(s.lexicon(field))
