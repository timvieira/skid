import re, os, sys
from argparse import ArgumentParser
from itertools import islice
from contextlib import contextmanager

from skid import index
from skid import add as _add
from skid import config
from skid.add import Document

from arsenal.terminal import cyan, yellow, magenta

from whoosh.searching import Hit


# TODO: I'd like to quickly check if I've added a paper before. Not sure hash
# equality is enough, but it's a start. Should have a quick way to do this at
# the prompt "skid similar doc.pdf" and "skid hash doc.pdf" checks for hash
# equality (do we want to download the paper and all that?).

def serve():
    """
    Fire-up web interface.
    """
    from skid.sandbox.web.serve import run
    run()


def add(source):
    """
    Add document from source. Sources can be urls or filenames.
    """
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
    """
    Display search results.
    """

    def link(x):
        if not x.startswith('http') and not x.startswith('file://'):
            # add file:// prefix to make file a link in the terminal
            return 'file://' + x
        return x

    def author(x):
        if not x.strip():
            return ''
        last = [a.strip().split()[-1] for a in x.split(';')]
        if len(last) == 1:
            return '%s' % last[0]
        elif len(last) == 2:
            return '%s & %s' % (last[0], last[1])
        else:
            return '%s et al.' % (last[0])

    for doc in islice(results, limit):

        hit = doc.parse_notes()

        if 'author' in show:
            a = author(hit.get('author', ''))
            if a:
                year = hit.get('year', '')
                if year:
                    a = '%s, %s' % (a, year)
                print (magenta % '(%s)' % a).encode('utf8'),

        if 'title' in show:
            print hit['title'].replace('\n', ' ').encode('utf8')

        if 'source' in show:
            print cyan % link(hit['source'])

        if 'cached' in show:
            print cyan % link(hit['cached'])

        if 'tags' in show:
            print hit['tags']

        if 'link' in show:
            if hit['source'].startswith('http'):
                print cyan % link(hit['source'])
            else:
                print cyan % link(hit['cached'])

        if 'link:notes' in show:
            print cyan % link(hit['cached'] + '.d/notes.org')

        if 'notes' in show:
            print hit['notes']

        if 'score' in show:
            print 'score:', hit.score

        print
    print


def org(results, limit=None, **kwargs):
    "Format results in org-mode markup."
    print
    for hit in islice(results, limit):
        source = hit['source']
        cached = hit['cached']
        d = cached + '.d'
        notes = d + '/notes.org'
        print ('\n+ %s' % hit['title']).encode('utf8')
        if hit['author']:
            print ('  ' + ' ; '.join('[[skid:author:"{0}"][{0}]]'.format(x.strip()) for x in hit['author'].split(';'))).encode('utf8')
        print ('  [[%s][directory]] | [[%s][source]] | [[%s][cache]] | [[%s][notes]]' % (d, source, cached, notes)).encode('utf8')
        if hit['tags']:
            print ' ', ' '.join('[[skid:tags:%s][%s]]' % (x,x) for x in hit['tags'].split()).encode('utf8').strip()


@contextmanager
def pager(name):
    """
    Wraps call to search_org. Redirects output to file and opens it in emacs.
    """
    sys.stdout = f = file('/tmp/foo', 'wb')
    yield
    sys.stdout.flush()
    sys.stdout = sys.__stdout__

    if name == 'less':
        os.system("less -R %s" % f.name)
    elif name == 'emacs':
        os.system("emacs -nw %s -e 'org-mode'" % f.name)
    else:
        raise Exception('Unknown option for pager %r' % name)


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


# TODO: use mtime in Whoosh index instead if "ls -t" and date-added file? (requires "skid update")
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


def completion():
    from os import environ, listdir
    if 'COMP_WORDS' in environ:                       # TODO: add filename completions (the bash default)
        cwords = environ['COMP_WORDS'].split()
        cline = environ['COMP_LINE']
        #cpoint = int(environ['COMP_POINT'])
        cword = int(environ['COMP_CWORD'])

        if cword >= len(cwords):
            currword = None
        else:
            currword = cwords[cword]

        if cword < 2:
            # second words is one of the skid commands like 'search' or 'add'
            cmds = [k for k,v in list(globals().iteritems()) if hasattr(v, '__call__')]
            possible = cmds

        elif 'skid add' in cline:
            possible = listdir('.')  # TODO: want the standard bash completion in this case

        else:
            possible = index.lexicon('author') + index.lexicon('title')

        if currword:
            possible = [x for x in possible if x.startswith(currword) and len(x) >= len(currword)]

        print ' '.join(possible).encode('utf8')


def lexicon(field):
    for x in index.lexicon(field):
        print x


def similar(cached, limit=config.LIMIT, numterms=40, fieldname='text', **kwargs):
    "Most similar results to cached document."
    ix = index.open_dir(index.DIRECTORY, index.NAME)
    with ix.searcher() as searcher:
        results = searcher.find('cached', unicode(cached))
        result = results[0]
        for hit in result.more_like_this(top=limit, numterms=numterms, fieldname=fieldname):
            yield hit


def main():
    if config.completion:
        completion()
        return

    commands = 'search, add, rm, update, drop, push, serve, ack, lexicon, ls'

    if len(sys.argv) <= 1:
        print commands
        return

    cmd = sys.argv.pop(1)

    if cmd in ('search', 'ls', 'similar'):

        p = ArgumentParser()
        p.add_argument('query', nargs='*')
        p.add_argument('--limit', type=int, default=config.LIMIT,
                       help='query limit (use 0 for no limit)')
        p.add_argument('--show', help='display options')
        p.add_argument('--hide', help='display options')
        p.add_argument('--pager', choices=('less', 'emacs'), default=None, help='pager for results')
        p.add_argument('--format', choices=('standard', 'org'), default='standard',
                       help='output format')
        p.add_argument('--by', choices=('relevance', 'modified', 'added'), default='relevance',
                       help='Sort results by')
        args = p.parse_args()

        query = ' '.join(args.query)

        limit = args.limit if args.limit > 0 else None

        # get list of results (convert Whoosh.searching.Hit to skid.Document)
        s = {'search': index.search, 'ls': ls, 'similar': similar}[cmd]
        results = list(map(todoc, s(query, limit=limit)))

        # sort documents according to '--by' criteria'
        sortwith = {'relevance': score, 'modified': modified, 'added': added}[args.by]
        if cmd == 'ls' and args.by == 'relevance':
            sortwith = added
        results.sort(key=sortwith, reverse=True)

        # limit number of search results
        results = results[:limit]

        if args.format == 'org':
            format = org
        else:
            format = display

        # process display options
        show = {'author', 'title', 'link', 'link:notes'}   # defaults
        show.update(x.strip() for x in (args.show or '').split(','))
        for x in (x.strip() for x in (args.hide or '').split(',')):
            if x in show:
                show.remove(x)

        if args.pager:
            with pager(args.pager):

                if args.format == 'org':
                    print '#+title: Search result for query %r' % query   # TODO: move this.
                    if limit:
                        print '# showing top %s results' % limit

                else:
                    print yellow % 'query: %r' % query
                    if limit:
                        print yellow % 'showing top %s results' % limit

                format(results, show=show)

        else:
            print yellow % 'query: %r' % query
            if limit:
                print yellow % 'showing top %s results' % limit
            format(results, show=show)

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

    else:
        print commands


if __name__ == '__main__':
    main()
