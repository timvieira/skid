import os, sys
from debug import ip
from automain import automain
from skid import pipeline, index, data, repair
from functools import wraps

def add(source):
    """
    Add document from source. Sources can be urls or filenames.
    """
    return pipeline.add(source, interactive=True)

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


if __name__ == '__main__':

    #try:
    #    mod = sys.argv[1]
    #    execfile(os.path.join(os.path.dirname(__file__), mod + '.py'))
    #except IndexError:
    #
    #    automain(available=[pipeline, index, data, repair])
    #except IOError:
    #    print 'command %r not recognized.' % mod
    #
    #else:
    automain()
