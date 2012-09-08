import os, sys
from debug import ip
from automain import automain
from skid import index
from skid import add as _add
from skid.config import ROOT, CACHE, REMOTE
from fsutils import cd
from subprocess import Popen, PIPE

def web():
    from skid.serve import run
    run()


def add(source):
    """
    Add document from source. Sources can be urls or filenames.
    """
    return _add.document(source, interactive=True)


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
                if k == 'cached':
                    val = 'file://' + val
                print '\033[31m%s\033[0m: %s' % (k, val.replace('\n', ' '))
        print
    print


# TODO: incremental indexing.
def update():
    """ Update index. """
    index.drop()
    index.build()


def push():
    "Use rsync to push data to remote machine."
    os.system('rsync -a %s/. %s/marks/.' % (CACHE, REMOTE))


def hg(*args):
    "Ask mercurial some questions"
    with cd(ROOT):
        os.system(' '.join(['hg'] + list(args)))


def recent():
    "List recently modified files."
    (out, err) = Popen(['ls', '-1t', CACHE], stdout=PIPE, stderr=PIPE).communicate()
    lines = [line for line in out.split('\n') if line.strip() and line.endswith('.d')]
    return lines


if __name__ == '__main__':
    automain()
