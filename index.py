"""
Index skid-marks to support efficient search over attributes including
full-text.
"""

import os
from datetime import datetime
from glob import glob

from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, KEYWORD, ID, DATETIME
from whoosh.qparser import QueryParser
from whoosh.qparser.dateparse import DateParserPlugin

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
                    title = TEXT(stored=True, spelling=True),
                    author = TEXT(stored=True, spelling=True),
                    notes = TEXT(stored=True, spelling=True),
                    text = TEXT(stored=True, spelling=True),
                    tags = KEYWORD(stored=True, spelling=True),
                    mtime = DATETIME(stored=True))
    create_in(DIRECTORY, schema, NAME)


def search(qstr):
    qstr = unicode(qstr.decode('utf8'))
    ix = open_dir(DIRECTORY, NAME)
    with ix.searcher() as searcher:
        # TODO: it would be nice to search other fields as well. In some cases
        # the text field id empty or even garbage, in which case if would be
        # nice to search the title as well. Idealy even we'd give things with
        # title match higher ranking.
        qp = QueryParser('text', schema=ix.schema)
        qp.add_plugin(DateParserPlugin(free=True, basedate=datetime.now()))
        q = qp.parse(qstr)

        for hit in searcher.search(q, limit=50):
            yield hit

        #print searcher.correct_query(q, qstr, allfields=True)


def drop():
    "Drop existing index."
    assert os.path.exists(DIRECTORY)
    os.system('rm -rf ' + DIRECTORY)
    print 'dropped index', DIRECTORY


# TODO: find files which might have been deleted they might still be living in
# the index. Currently, the only way to do this is by droping the index.

def update():
    "Rebuild index from scratch."

    # create index if it doesn't exist
    if not os.path.exists(DIRECTORY):
        create()

    # get handle to Whoosh index
    ix = open_dir(DIRECTORY, NAME)

    # TODO: quicker ways to update modified files: sort files by mtime; stop
    # updating at the first unchanged file.
    with ix.writer() as w, ix.searcher() as searcher:

        for cached in glob(CACHE + '/*'):

            if cached.endswith('.d'):   # only cached files, not the directories.
                continue

            # mtime of directory, not the cached file
            mtime = datetime.fromtimestamp(os.path.getmtime(cached + '.d'))

            # lookup document mtime in the index; don't add our extract info if
            # you don't need it.
            result = searcher.find('cached', unicode(cached))

            if not result:
                print '[INFO] new document', cached

            else:
                assert len(result) == 1, 'cached field should be unique.'
                result = result[0]
                if mtime <= result['mtime']:   # skip if document hasn't changed
                    continue

                print '[INFO] update to existing document:', cached

            text = file(cached + '.d/data/text').read().decode('utf8')
            meta = parse_notes(file(cached + '.d/notes.org').read())

            w.update_document(source = meta['source'],
                              title = meta['title'],
                              author = meta.get('author',u''),
                              cached = unicode(cached),
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
