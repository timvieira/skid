#!/usr/bin/env python
# -*- coding: utf-8 -*-
import skid.completion

import re, os, sys
from argparse import ArgumentParser
from itertools import islice
from contextlib import contextmanager
from collections import defaultdict

from skid import index
from skid import add as _add
from skid import config
from skid.add import Document
from skid.utils import bibkey, author

from arsenal.terminal import cyan, yellow, magenta, green, red

from whoosh.searching import Hit


# TODO: I'd like to quickly check if I've added a paper before. Not sure hash
# equality is enough, but it's a start. Should have a quick way to do this at
# the prompt "skid similar doc.pdf" and "skid hash doc.pdf" checks for hash
# equality (do we want to download the paper and all that?).

def serve():
    "Fire-up web interface."
    from skid.sandbox.web.serve import run
    run()


def add(source):
    "Add document from source. Sources can be urls or filenames."
    return _add.document(source, interactive=True)


def ack(x):
    """
    Search notes for pattern.

    TODO: not sure if this is any better than ``search``..
           - simple program; no need to update indexes

           - matches patterns: instead of keywords for more precise queries
             (lower recall), but does have some issues with multi-line.

           - Is this generally slower than equivalent keyword search?

    TODO: might want to ack text, not just notes.
    """
    os.system("find %s -name notes.org |xargs ack '%s'" % (config.CACHE, x))


def display(results, limit=None, show=('author', 'title', 'link', 'link:notes')):
    "Display search results."

    def link(x):
        if not x.startswith('http') and not x.startswith('file://'):
            # add file:// prefix to make file a link in the terminal
            return 'file://' + x
        return x


    for doc in islice(results, limit):

        hit = doc.parse_notes()

        if 'score' in show:
            print yellow % ('[%.2f]' % doc.score),

        if 'author' in show:
            a = author(hit['author'])
            if a:
                year = hit.get('year', '')
                if year:
                    a = '%s, %s' % (a, year)
                print (magenta % '(%s)' % a).encode('utf8'),

        if 'title' in show:
            #print
            #print 'latin1:', hit['title'].encode('latin1')
            #print 'utf8:  ', hit['title'].encode('utf8')
            print re.sub('\[\S+\]', lambda x: yellow % x.group(0),
                         hit['title'].strip()).replace('\n', ' ').encode('utf8')

        if 'source' in show:
            print cyan % link(hit['source'])

        if 'cached' in show:
            print cyan % link(hit['cached'])

        if 'link' in show:

            if hit['source'].startswith('http') and not hit['source'].endswith('.pdf'):
                print cyan % link(hit['source'])
            else:
                print cyan % link(hit['cached'])

        if 'link:notes' in show:
            print cyan % link(hit['cached'] + '.d/notes.org')

        if 'tags' in show:
            #print '%s%s%s' % (yellow % '[', (yellow % ', ').join(magenta % x for x in hit['tags']), yellow % ']')
            if hit['tags']:
                print (magenta % ', ').join(magenta % x for x in hit['tags'])

        if 'notes' in show:
            notes = hit['notes'].strip()
            if notes:
                for line in notes.split('\n'):
                    print yellow % ' |', line

        print
    print


def org(results, limit=None, **kwargs):
    "Format results in org-mode markup."
    print
    for doc in islice(results, limit):
        hit = doc.parse_notes()
        source = hit['source']
        cached = hit['cached']
        d = cached + '.d'
        notes = d + '/notes.org'
        print ('\n+ %s' % hit['title']).encode('utf8')
        if hit['author']:
            print ('  ' + ' ; '.join('[[skid:author:"\'{0}\'"][{0}]]'.format(x) for x in hit['author'])).encode('utf8')
        print ('  [[%s][directory]] | [[%s][source]] | [[%s][cache]] | [[%s][notes]]' % (d, source, cached, notes)).encode('utf8')
        if hit['tags']:
            print ' ', ' '.join('[[skid:tags:%s][%s]]' % (x,x) for x in hit['tags']).encode('utf8').strip()


@contextmanager
def pager(name='none'):
    """
    Wraps call to search_org. Redirects output to file and opens it in emacs.
    """

    if not name or name == 'none':
        yield
    else:

        if name not in ('emacs', 'less'):
            raise Exception('Unknown option for pager %r' % name)

        try:
            with file('/tmp/foo', 'wb') as f:
                sys.stdout = f
                yield
        finally:
            # make sure we stdout revert back
            sys.stdout = sys.__stdout__

        if name == 'less':
            os.system("less -RS %s" % f.name)
        elif name == 'emacs':
            os.system("emacs -nw %s -e 'org-mode'" % f.name)


def update():
    """ Update search index. """
    index.update()


def drop():
    "Drop search index. Don't worry you can always make another one by calling update."
    index.drop()


# Experimental: not sure what the best way to shuttle data around is nor how we
# want to do it.
def push():
    "Use rsync to push data to remote machine."
    os.system('rsync --progress -a %s/. %s/marks/.' % (config.CACHE, config.REMOTE))


def rm(cached):
    "Remove skid-mark associated with cached file."

    cached = cached.strip()
    cached = re.sub('^file://', '', cached)   # remove "file://" prefix

    assert cached.startswith(config.CACHE), \
        "This doesn't look like of skid's cached files."

    os.system('rm -f %s' % cached)     # remove cached file
    os.system('rm -rf %s.d' % cached)  # remove .d directory and all it's contents

    # remove file from whoosh index.
    index.delete(cached)


# TODO: use mtime/added in Whoosh index instead if "ls -t" and date-added file? (requires "skid update")
def added(d):
    return d.added

def modified(d):
    return d.modified

def score(d):
    return d.score

def todoc(d):
    if isinstance(d, Hit):
        doc = Document(d['cached'])
        doc.score = d.score
        return doc
    return d


def ls(q, **kwargs):
    "List recent files."
    for f in config.CACHE.files():
        if q in f:
            yield Document(f)


def lexicon(field):
    for x in index.lexicon(field):
        print x.encode('utf8')


def authors():

    def simplify(x):
        # simplify name: remove single initial, lowercase, convert to ascii
        return re.sub(r'\b[a-z]\.\s*', '', x.strip().lower()).encode('ascii', 'ignore')

    ix = defaultdict(list)
    docs = []  # documents with authors annotated

    for filename in config.CACHE.glob('*.pdf'):
        d = Document(filename)
        d.meta = d.parse_notes()
        authors = d.meta['author']
        if authors:
            docs.append(d)
            for x in authors:
                ix[simplify(x)].append(d)

    for a, ds in sorted(ix.items(), key=lambda x: len(x[1]), reverse=True):
        print yellow % '%s (%s)' % (a, len(ds))
        for d in ds:
            print ' ', d.meta['title'], magenta % ('(file://%s)' % d.cached)


def tags():
    ix = defaultdict(list)

    for filename in config.CACHE.glob('*.pdf'):
        d = Document(filename)
        d.meta = d.parse_notes()
        tags = d.meta['tags']
        if authors:
            for x in tags:
                ix[x.lower()].append(d)

    for tag, ds in sorted(ix.items(), key=lambda x: len(x[1]), reverse=True):
        print yellow % '%s (%s)' % (tag, len(ds))
        for d in ds:
            print ' ', d.meta['title'], magenta % ('(file://%s)' % (d.cached + '.d/notes.org'))



# TODO: We should probably just search Whoosh instead of contorting results the
# way I'm doing... in order to support ls (which could be done using Whoosh)
def main():

    if len(sys.argv) <= 1:
        print config.commands
        return

    cmd = sys.argv.pop(1)

    if cmd in ('search', 'ls', 'similar', 'key'):

        p = ArgumentParser()
        p.add_argument('query', nargs='*')
        p.add_argument('--limit', type=int, default=0, #config.LIMIT,
                       help='query limit (use 0 for no limit)')
        p.add_argument('--show', default='', help='display options')
        p.add_argument('--hide', default='', help='display options')
        p.add_argument('--pager', choices=('none', 'less', 'emacs'), default='less',
                       help='pager for results')
        p.add_argument('--format', choices=('standard', 'org'), default='standard',
                       help='output format')
        p.add_argument('--by', choices=('relevance', 'modified', 'added'), default='relevance',
                       help='Sort results by')
        p.add_argument('--top', action='store_true',
                       help='Only show top hit.')
        p.add_argument('--no-open', action='store_false',
                       help='do not open top hit')

        args = p.parse_args()

        query = ' '.join(args.query)

        limit = args.limit if args.limit > 0 else None


        # todo: support for bibtex key style search, e.g. 'bottou12counterfactual'
        #
        #   - convert 'bottou12counterfactual' into 'author:bottou year:2012 title:counterfactual'
        #
        #   - should be greedy e.g. act like '--top'
        #
        #   - bash completed for keys should be easy to implement and useful.

        if args.top:
            args.pager = 'none'
            limit = 1

        if cmd == 'search':
            results = index.search(query)

#        elif cmd == 'key':
#            p = bibkey(query)
#           if p:
#               q = 'author:%s year:%s title:%s' % p
#               print q
#               results = index.search(q)
#           else:
#               results = []

        elif cmd == 'similar':
            results = Document(query).similar(limit=limit)
        elif cmd == 'ls':
            results = ls(query)
        else:
            assert False, 'Unrecognized command %s' % cmd

        # convert results to list and convert Whoosh.searching.Hit to skid.Document
        results = list(map(todoc, results))

        # sort documents according to '--by' criteria'
        sortwith = {'relevance': score, 'modified': modified, 'added': added}[args.by]
        if cmd == 'ls' and args.by == 'relevance':
            sortwith = added
        results.sort(key=sortwith, reverse=True)

        nresults = len(results)

        # limit number of search results
        results = results[:limit]

        if args.format == 'org':
            format = org
        else:
            format = display

        # process display options
        show = {'author', 'title', 'link', 'link:notes'}   # defaults
        show.update(x.strip() for x in args.show.split(','))
        for x in (x.strip() for x in args.hide.split(',')):
            if x in show:
                show.remove(x)

        with pager(args.pager):
            if limit and len(results) >= limit:
                if args.format == 'org':
                    print '# showing top %s of %s results' % (min(limit, nresults), nresults)
                else:
                    print yellow % 'showing top %s of %s results' % (min(limit, nresults), nresults)
            format(results, show=show)

        if args.top:
            assert len(results) <= 1
            if not results:
                print red % 'Nothing found'
                return
            [top] = results
            # open cached document and user notes
#            os.system('gnome-open %s' % top.cached)
            if args.no_open:
                from subprocess import Popen
                Popen(['gnome-open', top.cached])
#            os.system('$EDITOR %s' % top.cached + '.d/notes.org')

    elif cmd == 'add':
        p = ArgumentParser()
        p.add_argument('source')
        args = p.parse_args()
        add(args.source)

    elif cmd == 'rm':
        p = ArgumentParser()
        p.add_argument('cached')
        args = p.parse_args()
        rm(args.cached)

    elif cmd == 'update':
        update()

    elif cmd == 'drop':
        drop()

    elif cmd == 'push':
        push()

    elif cmd == 'serve':
        serve()

    elif cmd == 'authors':
        authors()

    elif cmd == 'tags':
        tags()

    elif cmd == 'ack':
        p = ArgumentParser()
        p.add_argument('query')
        args = p.parse_args()
        ack(args.query)

    elif cmd == 'lexicon':
        p = ArgumentParser()
        p.add_argument('field')
        args = p.parse_args()
        lexicon(args.field)

    elif cmd == 'title':
        # doesn't require adding the document
        from skid.pdfhacks.pdfmill import extract_title
        p = ArgumentParser()
        p.add_argument('pdf')
        p.add_argument('--no-extra', action='store_false', dest='extra')
        args = p.parse_args()
        extract_title(args.pdf, extra=args.extra)

    else:
        print config.commands


if __name__ == '__main__':
    main()
