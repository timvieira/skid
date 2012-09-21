import os, sys
from debug import ip
from automain import automain
from skid import index
from skid import add as _add
from skid.config import ROOT, CACHE, REMOTE
from fsutils import cd
from subprocess import Popen, PIPE
from terminal import red, cyan

def web():
    from skid.serve import run
    with cd('/home/timv/projects/skid'):
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
        fields = ['title', 'cached', 'source', 'tags']
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


                print '%s: %s' % (red % k, val.replace('\n', ' '))
        print
    print


def update():
    """ Update index. """
    index.update()


def push():
    "Use rsync to push data to remote machine."
    os.system('rsync -a %s/. %s/marks/.' % (CACHE, REMOTE))


def hg(*args):
    "Ask mercurial some questions"
    with cd(ROOT):
        os.system(' '.join(['hg'] + list(args)))

def st(*args):
    "Ask mercurial some questions"
    with cd(ROOT):
        os.system(' '.join(['hg st'] + list(args)))


def recent():
    "List recently modified files."
    (out, err) = Popen(['ls', '-1t', CACHE], stdout=PIPE, stderr=PIPE).communicate()
    lines = [line for line in out.split('\n') if line.strip() and line.endswith('.d')]
    return lines


if __name__ == '__main__':
    automain()
