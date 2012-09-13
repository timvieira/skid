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
                    title = TEXT(stored=True, spelling=True),
                    description = TEXT(stored=True),
                    text = TEXT(stored=True, spelling=True),
                    mtime = DATETIME(stored=True),
                    tags = KEYWORD(stored=True, spelling=True))
    create_in(DIRECTORY, schema, NAME)


def search(qstr):
    qstr = unicode(qstr.decode('utf8'))
    ix = open_dir(DIRECTORY, NAME)
    with ix.searcher() as searcher:
        qp = QueryParser('text', schema=ix.schema)
        qp.add_plugin(DateParserPlugin(free=True, basedate=datetime.now()))
        q = qp.parse(qstr)
        for hit in searcher.search(q):
            yield hit

        #print searcher.correct_query(q, qstr, allfields=True)


def drop():
    "Drop existing index."
    assert os.path.exists(DIRECTORY)
    os.system('rm -rf ' + DIRECTORY)


def update():
    "Rebuild index from scratch."

    # create index if it doesn't exist
    if not os.path.exists(DIRECTORY):
        create()

    # get handle to Whoosh index
    ix = open_dir(DIRECTORY, NAME)

    # TODO: quicker ways to find modified files (sort files by mtime; stop
    # updating the index after the last modified file)
    with ix.writer() as w, ix.searcher() as searcher:

        for cached in glob(CACHE + '/*'):

            if cached.endswith('.d'):   # only cached files, not the directories.
                continue

            # mtime of directory, no the cached file
            mtime = datetime.fromtimestamp(os.path.getmtime(cached + '.d'))


            # lookup document mtime in the index; don't add our extract info if
            # you don't need it.

            result = searcher.find('cached', unicode(cached))


            if len(result) > 1:
                print '[ERROR] document indexed twice, but cached field should be unique.'
                print 'cached:', cached
                print 'results:', result
                ip()
                raise AssertionError


            if not result:
                print
                print '[INFO] new document', cached

            else:

                # TODO: Can we avoid doing two queries (get mtime and update)?
                result = result[0]
                if mtime <= result['mtime']:   # skip if document hasn't changed
                    continue

                print
                print '[INFO] update to existing document:', cached


            text = file(cached + '.d/data/text').read().decode('utf8')
            meta = parse_notes(file(cached + '.d/notes.org').read())

            w.update_document(source = meta['source'],
                              title = meta['title'],
                              cached = unicode(cached),
                              description = meta['description'],
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
