import os, sys
from debug import ip
from automain import automain


if __name__ == '__main__':

    try:
        mod = sys.argv[1]
        execfile(os.path.join(os.path.dirname(__file__),
                              mod + '.py'))

    except IndexError:
        from skid import pipeline, index, data, repair
        automain(available=[pipeline, index, data, repair])

    except IOError:
        print 'command %r not recognized.' % mod

    else:
        mod = sys.argv.pop(1)
        automain()
