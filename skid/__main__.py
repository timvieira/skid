#!/usr/bin/env python
# -*- coding: utf-8 -*-

import skid.completion
from skid import config
from skid.config import cmd

import re, os, sys
from argparse import ArgumentParser
from itertools import islice
from contextlib import contextmanager
from collections import defaultdict

from skid import index
from skid import add as _add
from skid.add import Document, SkidError
from skid.utils import bibkey, author

from arsenal.terminal import colors
from whoosh.searching import Hit

# TODO: I'd like to quickly check if I've added a paper before. Not sure hash
# equality is enough, but it's a start. Should have a quick way to do this at
# the prompt "skid similar doc.pdf" and "skid hash doc.pdf" checks for hash
# equality (do we want to download the paper and all that?).


def add(source, dest):
    "Add document from source. Sources can be urls or filenames."
    try:
        return _add.document(source, dest=dest, interactive=True)
    except SkidError as e:
        print('[%s] %s' % (colors.red % 'error', e))


def display(results, limit=None, show=('author', 'title', 'link', 'link:notes')):
    "Display search results."

    def link(x):
        if not x.startswith('http') and not x.startswith('file://'):
            # add file:// prefix to make file a link in the terminal
            return 'file://' + x
        return x

    for doc in islice(results, limit):

        hit = doc.parse_notes()

        # if whoosh reader is closed we can't access highlights
        if hasattr(doc, 'highlights'):
            print(doc.highlights.encode('utf8'))

        if 'score' in show:
            print(colors.yellow % ('[%.2f]' % doc.score), end=' ')

        if 'author' in show:
            a = author(hit['author'])
            if a:
                year = hit.get('year', '')
                if year:
                    a = '%s, %s' % (a, year)
                print((colors.magenta % '(%s)' % a), end=' ')

        if 'title' in show:
            print(re.sub('\[\S+\]', lambda x: colors.yellow % x.group(0),
                         hit['title'].strip()).replace('\n', ' '))

        if 'source' in show:
            print(colors.cyan % link(hit['source']))

        if 'cached' in show:
            print(colors.cyan % link(hit['cached']))

        if 'link' in show:

            if (hit['source'].startswith('http')           # show source for webpages,
                and not hit['cached'].endswith('.pdf')     # but not if it's a link to a pdf!
                and not hit['source'].endswith('.pdf')
            ):
                print(colors.cyan % link(hit['source']))
            else:
                print(colors.cyan % link(hit['cached']))

        if 'link:notes' in show:
            print(colors.cyan % link(hit['cached'] + '.d/notes.org'))

        if 'tags' in show:
            if hit['tags']:
                print((colors.magenta % ', ').join(colors.magenta % x for x in hit['tags']))

        if 'notes' in show:
            notes = hit['notes'].strip()
            if notes:
                for line in notes.split('\n'):
                    print(colors.yellow % ' |', line)

        print()
    print()


#def org(results, limit=None, **kwargs):
#    "Format results in org-mode markup."
#    print()
#    for doc in islice(results, limit):
#        hit = doc.parse_notes()
#        source = hit['source']
#        cached = hit['cached']
#        d = cached + '.d'
#        notes = d + '/notes.org'
#        print(('\n+ %s' % hit['title']).encode('utf8'))
#        if hit['author']:
#            print(('  ' + ' ; '.join('[[skid:author:"\'{0}\'"][{0}]]'.format(x) for x in hit['author'])).encode('utf8'))
#        print(('  [[%s][directory]] | [[%s][source]] | [[%s][cache]] | [[%s][notes]]' % (d, source, cached, notes)).encode('utf8'))
#        if hit['tags']:
#            print(' ', ' '.join('[[skid:tags:%s][%s]]' % (x,x) for x in hit['tags']).encode('utf8').strip())


def terminal_size(fd=1):
    """
    Returns height and width of current terminal. First tries to get
    size via termios.TIOCGWINSZ, then from environment. Defaults to 25
    lines x 80 columns if both methods fail.

    :param fd: file descriptor (default: 1=stdout)
    """
    try:
        import fcntl, termios, struct
        return struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
    except (IOError, ImportError):
        try:
            return (os.environ['LINES'], os.environ['COLUMNS'])
        except KeyError:
            return (25, 80)


@contextmanager
def pager(name='none', always=False):
    """
    Wraps call to search_org. Redirects output to file and opens it in emacs.
    """
    from tempfile import NamedTemporaryFile

    if not name or name == 'none':
        yield
    else:

        if name not in ('emacs', 'less'):
            raise Exception('Unknown option for pager %r' % name)

        try:
            #with open('/tmp/foo', 'wb') as f:
            with NamedTemporaryFile(delete=0, mode='w') as f:
                sys.stdout = f
                yield
        finally:
            # make sure we stdout revert back
            sys.stdout = sys.__stdout__

        try:
            with open(f.name) as f:
                lines = f.readlines()

            # TODO: what about lines that are too long? I don't think we can
            # break up file://links to multiple lines
            (h, _) = terminal_size()

            if len(lines) + 4 > h or always:
                if name == 'less':
                    os.system("less -RS %s" % f.name)
                elif name == 'emacs':
                    os.system("emacs -nw %s -e 'org-mode'" % f.name)
            else:
                print()
                print(''.join(lines).strip())
                print()

        finally:
            if os.path.exists(f.name):
                os.unlink(f.name)


def rm(q):
    "Remove skid-mark associated with cached file."

    cached = q.strip()
    cached = re.sub('^file://', '', cached)   # remove "file://" prefix

    if cached.startswith(config.CACHE):
        # remove cached file
        os.system('rm -f %s' % cached)
        # remove corresponding '.d' directory and its contents
        os.system('rm -rf %s.d' % cached)
        # remove file from whoosh index.
        index.delete(cached)

    else:
        from skid.index import search
        results = [dict(x) for x in search(q)]
        if len(results) == 0:
            # Should only happen if user hasn't done run skid-update since
            # adding the paper being deleted.
            print('No matches. Make sure skid is up-to-date by running `skid update`.')
        elif len(results) == 1:
            [hit] = results
            print()
            print(hit['title'])
            print(colors.green % "Are you sure you'd like to delete this document [Y/n]?", end=' ')
            if input().strip().lower() in ('y','yes',''):
                if rm_cached(hit['cached']):
                    print(colors.yellow % 'Successfully deleted.')
        else:
            assert False, 'Multiple (%s) results found for query %r. ' \
                'Refine query and try again.' \
                % (len(results), q)


def rm_cached(cached):
    "Remove skid-mark associated with cached file."

    cached = cached.strip()
    cached = re.sub('^file://', '', cached)   # remove "file://" prefix

    assert cached.startswith(config.CACHE), \
        "This doesn't look like of skid's cached files."

    os.system('rm -f %s' % cached)     # remove cached file
    os.system('rm -rf %s.d' % cached)  # remove .d directory and all it's contents

    # remove file from whoosh index.
    return index.delete(cached)


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
        doc.hit = d
        # very slow...
        #doc.highlights = re.sub('<b class="match.*?>([\w\W]+?)</b>',
        #                        r'\033[31m\1\033[0m',
        #                        d.highlights('text', top=3)).replace('\n', ' ') + '\n'
        return doc
    return d


def ls(q, **kwargs):
    "List recent files."
    for f in config.CACHE.files():
        if q in f:
            yield Document(f)


def lexicon(field):
    for x in index.lexicon(field):
        print(x.decode('utf-8'))


def authors():

    def simplify(x):
        # simplify name: remove single initial, lowercase, convert to ascii
        return re.sub(r'\b[a-z]\.\s*', '', x.strip().lower()).encode('ascii', 'ignore').decode('ascii')

    ix = defaultdict(list)
    docs = []  # documents with authors annotated

    collisions = defaultdict(set)

    for filename in config.CACHE.glob('*.pdf'):
        d = Document(filename)
        d.meta = d.parse_notes()
        A = d.meta['author']
        if A:
            docs.append(d)
            for x in A:
                ix[simplify(x)].append(d)
                collisions[simplify(x)].add(x)

    for a, ds in sorted(list(ix.items()), key=lambda x: len(x[1]), reverse=True):
        print(colors.yellow % '%s (%s)' % (a, len(ds)))
        for d in ds:
            print(' ', d.meta['title'], colors.magenta % ('(file://%s)' % d.cached))


def tags():
    ix = defaultdict(list)

    for filename in config.CACHE.glob('*.pdf'):
        d = Document(filename)
        d.meta = d.parse_notes()
        T = d.meta['tags']
        if T:
            for x in T:
                ix[x.lower()].append(d)

    for tag, ds in sorted(list(ix.items()), key=lambda x: len(x[1]), reverse=True):
        print(colors.yellow % '%s (%s)' % (tag, len(ds)))
        for d in ds:
            print(' ', d.meta['title'], colors.magenta % ('(file://%s)' % (d.cached + '.d/notes.org')))



# TODO: We should probably just search Whoosh instead of contorting results the
# way I'm doing... in order to support ls (which could be done using Whoosh)
def main():

    if len(sys.argv) <= 1:
        print(', '.join(sorted(cmd.ALL)))
        return

    command = sys.argv.pop(1)

    if command in (cmd.search, cmd.ls, cmd.similar, cmd.key):

        p = ArgumentParser()
        p.add_argument('query', nargs='*')
        p.add_argument('--limit', type=int, default=0, #config.LIMIT,
                       help='query limit (use 0 for no limit)')
        p.add_argument('--show', default='', help='display options')
        p.add_argument('--hide', default='', help='display options')

        # TODO: pager temporarily disabled because of transition to python3
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
        p.add_argument('--note', action='store_true',
                       help='Open note for top hit in editor.')

        args = p.parse_args()

        query = ' '.join(args.query)

        limit = args.limit if args.limit > 0 else None

        if args.top:
            args.pager = 'none'
            limit = 1

        if command == cmd.search:
            results = index.search(query)

        elif command == cmd.key:
            # Supports bibtex key search, e.g. 'bottou12counterfactual'
            #
            #  Example key
            #
            #   'bottou12counterfactual'
            #   -> 'author:bottou year:2012 title:counterfactual'
            #
            #   - should be greedy e.g. act like '--top'
            #
            #   - bash completion for keys should be easy to implement and useful.
            #
            p = bibkey(query)
            if p:
                # TODO: this version doesn't search for papers where author is first-author
                q = ' '.join('%s:%s' % (k,v) for (k,v) in zip(['author', 'year', 'title'], p) if v)
                print(q)
                results = index.search(q)
            else:
                results = []

        elif command == cmd.similar:
            results = Document(query).similar(limit=limit)
        elif command == cmd.ls:
            results = ls(query)
        else:
            assert False, 'Unrecognized command %s' % command

        # convert results to list and convert Whoosh.searching.Hit to skid.Document
        results = list(map(todoc, results))

        # sort documents according to '--by' criteria'
        sortwith = {'relevance': score, 'modified': modified, 'added': added}[args.by]
        if command == cmd.ls and args.by == 'relevance':
            sortwith = added
        results.sort(key=sortwith, reverse=True)

        nresults = len(results)

        # limit number of search results
        results = results[:limit]

        if args.format == 'org':
            fmt = org
        else:
            fmt = display

        # process display options
        show = {'author', 'title', 'link', 'link:notes'}   # defaults
        show.update(x.strip() for x in args.show.split(','))
        for x in (x.strip() for x in args.hide.split(',')):
            if x in show:
                show.remove(x)

        with pager(args.pager):
            if limit and len(results) >= limit:
                if args.format == 'org':
                    print('# showing top %s of %s results' % (min(limit, nresults), nresults))
                else:
                    print(colors.yellow % 'showing top %s of %s results' % (min(limit, nresults), nresults))
            fmt(results, show=show)

        if args.top:
            assert len(results) <= 1
            if not results:
                print(colors.red % 'Nothing found')
                return
            [top] = results
            # open top hit
            if args.no_open:
                if args.note:
                    # open user's note in editor
                    os.system('$EDITOR %s' % top.cached + '.d/notes.org')
                else:
                    from subprocess import Popen
                    # open cached document
                    # TODO: read from config file
                    Popen(['xdg-open', top.cached])

    elif command == cmd.add:
        p = ArgumentParser()
        p.add_argument('source')
        p.add_argument('--name')
        args = p.parse_args()
        add(args.source, dest=args.name)

    elif command == cmd.rm:
        p = ArgumentParser()
        p.add_argument('cached')
        args = p.parse_args()
        rm(args.cached)

    elif command == cmd.update:
        index.update()

    elif command == cmd.authors:
        authors()

    elif command == cmd.tags:
        tags()

    elif command == cmd.drop:
        print(colors.yellow % 'Dropping search index... To build a fresh one run\n$ skid update')
        index.drop()

    elif command == cmd.lexicon:
        p = ArgumentParser()
        p.add_argument('field')
        args = p.parse_args()
        lexicon(args.field)

    elif command == cmd.title:
        # doesn't require adding the document, just finds the title.
        from skid.pdfhacks.pdfmill import extract_title
        p = ArgumentParser()
        p.add_argument('pdf')
        p.add_argument('--no-extra', action='store_false', dest='extra')
        args = p.parse_args()
        extract_title(args.pdf, extra=args.extra)

    elif command == cmd.scholar:
        from skid.add import gscholar_bib
        from skid.pdfhacks.pdfmill import extract_title
        p = ArgumentParser()
        p.add_argument('pdf')
        p.add_argument('--no-extra', action='store_false', dest='extra')
        args = p.parse_args()

        # run google scholar search based on extracted title.
        title = extract_title(args.pdf, extra=args.extra)
        gscholar_bib(title=title)

    else:
        print(', '.join(sorted(cmd.ALL)))


if __name__ == '__main__':
    main()
