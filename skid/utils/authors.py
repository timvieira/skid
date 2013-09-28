#!/usr/bin/env python
"""

TODO:
  - author deduplication use simple shingle overlap to cluster
  - fixed silly layout (double edges look ugly)
  - graph mining using networkx

  - citation graph: (could use a classifier with features based on title
    substring overlap, author). most papers in the citation graph will not
    appears in my skid marks. But, the idea is that if paper is cited by many in
    my collection, I might want to make sure I've read it (or at least intend
    to).

"""
import re, os
from skid.config import CACHE
from skid.add import Document
from collections import defaultdict
from urllib import quote

def simplify(x):
    # simplify name: remove single initial, lowercase, convert to ascii
    return re.sub(r'\b[a-z]\.\s*', '', x.strip().lower()).encode('ascii', 'ignore')

def data():
    ix = defaultdict(list)
    docs = []  # documents with authors annotated

    for filename in CACHE.glob('*.pdf'):
        d = Document(filename)
        d.meta = d.parse_notes()
        authors = d.meta['author']
        if authors:
            docs.append(d)
            for x in authors:
                ix[simplify(x)].append(d)

    return ix, docs


def top():
    ix, _ = data()
    for author, ds in sorted(ix.items(), key=lambda x: len(x[1])):
        print '%s (%s)' % (author, len(ds))
        for d in ds:
            print ' ', d.meta['title']


def coauthors():
    _, docs = data()
    with file('coauthors.dot', 'wb') as dot:
        print >> dot, 'graph coauthors {'
        for i, d in enumerate(docs):
            print >> dot, '"%s" [shape=box,width=0.1];' % i
            for author in d.meta['author']:
                author = simplify(author)
                # if I don't add edges in both directions graphviz gives me a
                # bipartite layout.
                print >> dot, ('"%s" -- %s;' % (author, i)).encode('ascii', 'ignore')
                print >> dot, ('%s -- "%s";' % (i, author)).encode('ascii', 'ignore')
        print >> dot, '}'

    os.system('dot -Tsvg coauthors.dot > coauthors.svg')

    with file('coauthors.svg') as f:
        svg = f.read()

    html = re.sub('^([\w\W]*)(<svg )', r'\2', svg)

    def add_handle(match):
        (x, _, text) = match.groups()
        try:
            paperid = int(text)
        except ValueError:
            return x
        title = docs[paperid].meta['title']
        return re.sub('<g ', '<g onclick="alert(unescape(\'%s\'))" ' % quote(title), x)

    p = re.compile('(<g id="(.*?)" class="node">[\s\n\r]*<title>(.*?)</title>[\w\W]*?</g>)')

    html = p.sub(add_handle, html)

    with file('coauthors.html','wb') as f:
        f.write('<html><body>\n')
        f.write(html)
        f.write('</body></html>')


if __name__ == '__main__':
    top()
    coauthors()
