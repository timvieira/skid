import os, sys
from debug import ip
from automain import automain
from skid import index
from skid import add as _add
from skid.config import ROOT, CACHE, REMOTE
from fsutils import cd
from subprocess import Popen, PIPE
from terminal import red, cyan


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


def ack(*x):
    """
    Search notes for pattern.

    TODO: not sure if this is any better than ``search``..
           - simple program; no need to update indexes

           - matches patterns: instead of keywords for more precise queries
             (lower recall), but does have some issues with multi-line.

           - Is this generally slower than equivalent keyword search?

    TODO: might want to ack text, not just notes.
    """
    os.system("find %s -name notes.org |xargs ack '%s'" % (CACHE, ' '.join(x)))


# TODO: I think dumping everything to the screen isn't the best idea. We should
# have some command-line options (-v: verbose; -s: sources; -d: directory, -n:
# notes, etc). By default we should list the preferred link type (for pdfs this
# should be the cached document; links and notes should be the source).
def search(*q):
    """
    Search skid-marks plain-text or metadata.
    """
    q = ' '.join(q)
    print
    print 'query:', q

    for hit in index.search(q):
        fields = ['title', 'author', 'cached', 'source', 'tags']
        for k in fields:
            val = hit[k].strip()
            if val and k != 'text':
                if k in ('source', 'cached'):
                    # add file:// prefix if file, http other wise
                    if not val.startswith('http') and not val.startswith('file://'):
                        val = 'file://' + val
                if k == 'cached':
                    # also print a 'link' to the notes file.
                    print '%s: %s' % (red % 'notes', cyan % (val + '.d/notes.org'))
                    print '%s: %s' % (red % 'd', cyan % (val + '.d/'))
                if k in ('cached', 'source'):
                    val = cyan % val   # color 'links'
                print ('%s: %s' % (red % k, val.replace('\n', ' '))).encode('utf8')
        print
    print


def search_org(*q):
    """
    Search skid-marks for particular attributes. Output org-mode friendly
    output.
    """
    q = ' '.join(q)
    print
    print '#+title: Search result for query %r' % q
    for hit in index.search(q):
        source = hit['source']
        cached = hit['cached']
        d = cached + '.d'
        notes = d + '/notes.org'
        print ('\n+ %s' % hit['title']).encode('utf8')
        if hit['author']:
            print ('  ' + ' ; '.join('[[skid:author:"{0}"][{0}]]'.format(x.strip()) for x in hit['author'].split(';'))).encode('utf8')
        print ('  [[%s][directory]] [[%s][source]] [[%s][cache]] [[%s][notes]]' % (d, source, cached, notes)).encode('utf8')
        if hit['tags']:
            print ' ', ' '.join('[[skid:tags:%s][%s]]' % (x,x) for x in hit['tags'].split()).encode('utf8').strip()


def search1(*q):
    sys.stdout = f = file('/tmp/foo', 'wb')
    search_org(*q)
    os.system("emacs -nw /tmp/foo -e 'org-mode'")
    sys.stdout = sys.__stdout__


def update():
    """ Update index. """
    index.update()


def drop():
    "Drop index. Don't worry you can always make another one."
    index.drop()


def push():
    "Use rsync to push data to remote machine."
    os.system('rsync --progress -a %s/. %s/marks/.' % (CACHE, REMOTE))


def hg(*args):
    "Ask mercurial some questions"
    with cd(ROOT):
        os.system(' '.join(['hg'] + list(args)))


def st(*args):
    "Ask mercurial some questions"
    with cd(ROOT):
        os.system(' '.join(['hg st'] + list(args)))


def checkpoint():
    with cd(ROOT):
        os.system("hg addremove && hg ci -m '()'")


# todo: what I really want is something like "hg log" which lists a summary of
# everything I've done.
def recent():
    "List recently modified files."
    (out, err) = Popen(['ls', '-1t', CACHE], stdout=PIPE, stderr=PIPE).communicate()
    lines = [line for line in out.split('\n') if line.strip() and line.endswith('.d')]
    return lines


cmds = [k for k,v in list(globals().iteritems()) if hasattr(v, '__call__')]

def main():
    from os import environ, listdir
    if 'COMP_WORDS' in environ:                       # TODO: add filename completions (the bash default)
        cwords = environ['COMP_WORDS'].split()
        cline = environ['COMP_LINE']
        cpoint = int(environ['COMP_POINT'])
        cword = int(environ['COMP_CWORD'])

        if cword >= len(cwords):
            currword = None
        else:
            currword = cwords[cword]

        if cword < 2:
            possible = cmds

        elif 'skid add' in cline:
            possible = listdir('.')

        else:
            possible = index.lexicon('author') + index.lexicon('title')

        if currword:
            possible = [x for x in possible if x.startswith(currword) and len(x) >= len(currword)]

        print ' '.join(possible).encode('utf8')

        sys.exit(1)

    import skid.__main__
    automain(mod=skid.__main__)

if __name__ == '__main__':
    main()
