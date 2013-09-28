from glob import glob
from collections import defaultdict
from skid.config import CACHE


def find_orphans():
    "Cleanup: find stray directories or files in cache."
    ds = set()
    xs = set()
    for x in glob(CACHE + '/*'):
        if x.endswith('.d'):
            ds.add(x[:-2])
        else:
            xs.add(x)
    for x in ds.symmetric_difference(xs):
        print x


# TODO: how should we merge these documents?
def hash_collisions():
    "Find hash collisions in corpus."
    d = defaultdict(list)
    for x in glob(CACHE + '/*/data/hash'):
        d[file(x).read().strip()].append(x)

    for k,v in d.iteritems():
        if len(v) > 1:
            print k

            v = [z[:-12] for z in v]

            for z in v:
                print '  ', 'file://' + z

            notes = [f + '.d/notes.org' for f in v]

            assert len(v) == 2

            """
            from skid.add import merge_kdiff3
            with file(notes[0]) as f:
                foo = f.read()
            try:
                merge_kdiff3(foo, notes[1])
            except AssertionError:
                continue
            else:

                # XXX: only prints the stuff to delete... needs testing
                print 'rm -rf ' + notes[0][:-12] + '*'
            """

if __name__ == '__main__':
    from arsenal.automain import automain
    automain()
