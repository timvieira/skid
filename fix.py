import re, os
from glob import glob
from collections import defaultdict
from skid.config import CACHE
from debug import ip


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
            for z in v:
                f = z[:-12]
                print '  ', 'file://' + f
