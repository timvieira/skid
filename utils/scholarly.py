from skid import config
from skid.add import Document

from skid.utils.gscholar import pdflookup, query
from arsenal.terminal import *
from datetime import datetime

from random import shuffle

files = config.CACHE.files()

shuffle(files)

for f in files:

    if not f.endswith('.pdf'):
        continue

    d = Document(f)

    meta = d.parse_notes()

    print green % ('file://' + d.cached)
    print yellow % meta['title']
    print yellow % ' ; '.join(meta['author'])

    results = query(meta['title'])
    print len(results), 'results'
    for x in results:
        print x

    break
