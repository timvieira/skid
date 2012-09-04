import os, sys
from debug import ip
from automain import automain
from skid import index
from skid import add as _add
from functools import wraps
from skid.config import CACHE, REMOTE

def add(source):
    """
    Add document from source. Sources can be urls or filenames.
    """
    return _add.document(source, interactive=True)


def search(*q):
    """
    Search collection for query
    """
    index.search(' '.join(q))


# TODO: incremental indexing.
def update():
    """ Update index. """
    index.drop()
    index.build()


def push():
    "Use rsync to push data to remote machine."
    os.system('rsync -a %s/. %s/marks/.' % (CACHE, REMOTE))


if __name__ == '__main__':
    automain()
