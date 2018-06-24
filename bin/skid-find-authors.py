#!/usr/bin/env python
import re, os
from collections import defaultdict
from arsenal.misc import browser
from skid import config
from skid.add import Document

def main(filename):

    ix = defaultdict(list)
    docs = []  # documents with authors annotated

    for cached in config.CACHE.glob('*.pdf'):
        d = Document(cached)
        d.meta = d.parse_notes()
        authors = d.meta['author']
        if authors:
            docs.append(d)
            for x in authors:
                ix[x].append(d)

    hits = defaultdict(list)

    def hit(m):
        name = m.group(1)
        link = '%s' % hit.id
        hits[name].append(link)
        hit.id += 1
        return r'<a name="{link}" style="background-color: red; color: white;">{name}</a>'.format(name=name, link=link)

    hit.id = 0

    if filename.startswith('http'):
        from arsenal.download import urlread
        [_,_,content] = urlread(filename)
    else:
        content = open(filename).read()

    out = re.sub('(%s)' % '|'.join(sorted(ix.keys(), key=lambda x: (len(x), x))),
                 hit,
                 content.decode('ascii','ignore'))

    stuff = '<br/>'.join('%s: %s' % (name, ' '.join('<a href="#%s">%s</a>' % (l,l) for l in links)) for name, links in sorted(hits.items()))

    sty = 'border: thin solid #000; width: 300px; top: 10px; right: 10px; position: absolute; z-index: 100; background-color: white; padding: 10px;'
    stuff = '<div style="%s">%s</div>' % (sty, stuff)

    out = re.sub('(<body.*?>)', r'\1 %s' % stuff, out)

    if os.path.exists(filename):
        with open('skid-' + filename, 'wb') as f:
            f.write(out)

    browser(out)


if __name__ == '__main__':
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument('filename')
    args = p.parse_args()
    main(args.filename)
