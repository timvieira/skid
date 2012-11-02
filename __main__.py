import os, sys
from debug import ip
from automain import automain
from skid import index
from skid import add as _add
from skid.config import ROOT, CACHE, REMOTE
from fsutils import cd
from subprocess import Popen, PIPE
from terminal import red, cyan


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
    os.system('find %s -name notes.org |xargs ack %s' % (CACHE, ' '.join(x)))


def search(*q):
    """
    Search skid-marks for particular attributes.
    """
    q = ' '.join(q)
    print
    print 'query:', q
    for hit in index.search(q):
        print 'docnum:', hit.docnum
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


def search1(*q):
    """
    Search skid-marks for particular attributes. Output org-mode friendly
    output.

    Example usage:

      $ skid search1 machine learning > /tmp/foo && emacs -nw /tmp/foo -e 'org-mode'

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


def search2(*q):
    sys.stdout = f = file('/tmp/foo', 'wb')
    search1(*q)
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


# todo: what I really want is something like "hg log" which lists a summary of
# everything I've done.
def recent():
    "List recently modified files."
    (out, err) = Popen(['ls', '-1t', CACHE], stdout=PIPE, stderr=PIPE).communicate()
    lines = [line for line in out.split('\n') if line.strip() and line.endswith('.d')]
    return lines


if __name__ == '__main__':
    automain()
