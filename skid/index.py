#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Index skid-marks to support efficient search over attributes including
full-text.
"""

import re, os

from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID, DATETIME
from whoosh.qparser import QueryParser, MultifieldParser
from whoosh.analysis import KeywordAnalyzer, STOP_WORDS

from skid.utils import remove_stopwords
from skid.config import ROOT, CACHE
from skid.add import Document

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
                    hash = ID(stored=True, unique=True),
                    title = TEXT(stored=True),
                    author = TEXT(stored=True),
                    year = TEXT(stored=True),
                    notes = TEXT(stored=True),
                    text = TEXT(stored=True),
                    tags = TEXT(stored=True, analyzer=KeywordAnalyzer()),
                    added = DATETIME(stored=True),
                    mtime = DATETIME(stored=True))
    create_in(DIRECTORY, schema, NAME)


def search(q, limit=None):
    q = unicode(q.decode('utf8'))
    ix = open_dir(DIRECTORY, NAME)
    with ix.searcher() as searcher:
        qp = MultifieldParser(fieldnames=['title', 'author', 'tags', 'notes', 'text'],
                              fieldboosts={'title':  7,
                                           'author': 10,
                                           'tags':   4,
                                           'notes':  2,
                                           'text':   1},
                              schema=ix.schema)

        # Whoosh chokes on queries with stop words, so remove them.
        q = remove_stopwords(q)

        q = qp.parse(q)
        for hit in searcher.search(q, limit=limit):
            yield hit


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
    ix = open_dir(DIRECTORY, NAME)
    with ix.searcher() as searcher, ix.writer() as w:
        qp = QueryParser(u'cached', ix.schema)
        q = qp.parse(unicode(cached))
        results = searcher.search(q)
        if len(results) == 0:
            # Should only happen if user hasn't done run skid-update since
            # adding the paper being deleted.
            print 'Cached file %r not found in index.' % cached
        elif len(results) == 1:
            w.delete_document(results[0].docnum)
        else:
            assert False, 'This should never happen. ' \
                'Multiple (%s) results for %r found for cached file.' % (len(results), cached)


def update():
    "Update index."

    # create index if it doesn't exist
    if not DIRECTORY.exists():
        create()

    # get handle to Whoosh index
    ix = open_dir(DIRECTORY, NAME)

    with ix.writer() as w, ix.searcher() as searcher:

        # sort cached files by mtime.
        files = [Document(f) for f in CACHE.files()]
        files.sort(key = (lambda x: x.modified), reverse=True)

        for d in files:

            # lookup document mtime in the index; don't add or extract info if
            # you don't need it.
            result = searcher.find('cached', unicode(d.cached))

            if not result:
                print '[INFO] new document', d.cached

            else:
                assert len(result) == 1, 'cached should be unique.'
                result = result[0]
                if d.modified <= result['mtime']:   # already up to date

                    # Since we've sorted files by mtime, we know that files
                    # after this one are older, and thus we're done.
                    return

                print '[INFO] update to existing document:', d.cached

            meta = d.parse_notes()

            # just a lint check
            assert meta['cached'] == d.cached, \
                'Cached field in notes (%s) ' \
                'does not match associated file (%s) ' \
                'in notes file %r' % (meta['cached'],
                                      d.cached,
                                      'file://' + d.d/'notes.org')

            w.update_document(source = meta['source'],
                              cached = unicode(d.cached),
                              hash = d.hash(),
                              title = meta['title'],
                              author = u' ; '.join(meta['author']),
                              year = meta['year'],
                              notes = meta['notes'],
                              text = d.text(),
                              mtime = d.modified,
                              added = d.added,
                              tags = u' '.join(meta['tags']))


def lexicon(field):
    """
    List lexicon entries from field. For example lexicon('tags') should return
    all know tags.
    """
    ix = open_dir(DIRECTORY, NAME)
    with ix.searcher() as s:
        return list(s.lexicon(field))
