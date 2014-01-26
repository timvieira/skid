#!/usr/bin/env python
"""
Unfinished

Half-baked idea to provide bibkeys for skid documents. These keys can be used
for rapid access to skid documents (with quick bash completion).
"""

import re
from skid import config
from skid.add import Document
from skid.utils import lastname, remove_stopwords
from arsenal.misc import ctx_redirect_io
from arsenal.terminal import yellow

def dump():

    for f in config.CACHE.files():
        d = Document(f)
        m = d.parse_notes()

        if not m['author']:   # skip skid marks with out annotated authors.
            continue

        author = ' '.join(map(lastname, m['author']))

        title = remove_stopwords(m['title'])
        title = re.findall('\w+', title)

        year = m['year'][-2:]

        title = ' '.join(title)

        author = author.replace('-', ' ')
        title = title.replace('-', ' ')
        year = year.replace('-', ' ')

        key = '%s-%s-%s' % (author, year, title)
        key = key.lower()
        print key.encode('utf8')


if __name__ == '__main__':
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument('action', choices=('dump', 'search', 'complete'))
    p.add_argument('filters', nargs='*', help='filters, each is a regex')
    args = p.parse_args()

    d = config.ROOT / 'bibkeys'
    if args.action == 'dump':
        with ctx_redirect_io(file(d, 'wb')) as f:
            dump()

    else:
        # TODO: consider ordered completions "author - year - title"
        from env.bin.filter import main
        with file(d) as f:
            matches = list(main(args.filters, f.readlines(), color=args.action != 'complete'))
            for m in matches:
                print yellow % m

                [a, y, t] = m.split('-')

                q = ''
                if a:
                    q += ''.join(map(' author:%s'.__mod__, a.split(' ')))

                if t:
                    q += ''.join(map(' title:%s'.__mod__, t.split(' ')))
                if y:
                    q += " year:'*%s'" % y

                skidq = 'skid search --pager=none %s' % q

                import os
                os.system(skidq)
