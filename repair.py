import re, os
from glob import glob
from collections import defaultdict
from skid.config import CACHE
from debug import ip

def find_stuff_to_describe():
    "Automatically find documents to write descriptions for."
    for filename in glob(CACHE + '/*.pdf'):
        print filename
        assert os.path.exists(filename + '.d')

        description = filename + '.d/description'

        if file(description).read().strip():  # has description
            continue

        os.system('gnome-open ' + filename + ' 2>/dev/null &')

        os.system('/home/timv/projects/env/bin/visit ' + description)
        raw_input('hit enter for next')


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
        #assert x in ds
        #os.system('rm -r ' + x + '.d')
        print x


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
