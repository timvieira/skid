import re
import cPickle as pickle
from skid.add import Document
from skid.pdfhacks.pdfmill import convert
from arsenal.iterextras import iterview
from arsenal.terminal import red, green, yellow, blue
from skid.config import CACHE


def data(debug=False):

    for filename in CACHE.glob('*.pdf'):

        if debug:
            print filename

        d = Document(filename)
        meta = d.parse_notes()

        if meta.get(u'author', None):

            if debug:
                print
                print meta.get(u'title', None)
                print meta.get(u'author', None)
                print

#            try:
            pdf = convert(filename)
#            except:
#                if debug:
#                    print red % 'FAIL', filename
#                continue

            yield (meta, d, pdf)


def shingle(x, size=3):
    """
    >>> shingle("abcdef", size=3)
    ['abc', 'bcd', 'cde', 'def']
    """
    return [x[i:i + size] for i in xrange(0, len(x) - size + 1)]


def find_authors(meta, d, pdf):

    print '====================================='
    print 'file://' + d.cached

    print meta['title'].encode('utf8')
    print meta['author'].encode('utf8')

    lines = []

    author = d.parse_notes()['author']
    authors = [set(shingle(x.strip())) for x in author.split(';')]

    if not pdf:
        return

    for x in pdf.pages[0].items:

        if 'text' not in x.attributes:
            continue

        text = x.attributes['text']
        text = re.sub(',', ' ', text)
        text = text.encode('utf8', 'ignore')  # HACK: ignores non-ascii

        b = shingle(x.attributes['text'])
        b = set(b)

        if not b:
            continue

        distance = sum(-len(a & b) * 1.0 / len(a | b) for a in authors)

        if distance > -0.2:
            x.attributes['author'] = False
            continue

        if distance >= 0:
            x.attributes['author'] = False
            continue

        lines.append(((distance, -x.attributes['font-size']), x))

    # ERRORS:
    #  - copyright
    #  - emails
    #  - citations
    #  - sometimes author have same font, but different fontsize (even though it
    #    looks the same size in the pdf)

    # TODO:
    #  - check for n-grams explained in author string.

    if not lines:
        print red % 'Sorry, no lines in the document :-('
        return

    lines.sort()
    print

    font_name = lines[0][1].attributes.get('font-name', None)
    font_size = lines[0][1].attributes.get('font-size', None)


    extracted = []

    for (distance, _), item in lines[:10]:  # most similar lines

        x = item.attributes
        print '  %6.4f' % distance,

        text = x['text'].encode('utf8')

        info = x.copy()
        info.pop('text')

        if x['font-name'] == font_name and x['font-size'] == font_size:
            print green % text, info
            extracted.append(text)

            x['author'] = True

        else:
            print red % text, info

    print

    # TODO: check if there is still an entire name with no good match.

    if not extracted:
        print red % 'failed to extract anything relevant :-('
        return

    c = reduce(set.union, map(set, map(shingle, extracted)))

    tally = [0]*len(author)
    size = 3
    for i in xrange(len(author)):
        if author[i:i+size] in c:
            for j in xrange(i, i+size):
                tally[j] += 1

    print ''.join(color(c, 1 - x*1.0/3) for c, x in zip(author, tally))

    return True


import fabulous
def color(c, x):
    "Colorize numbers in [0,1] based on value; darker means smaller value."
    a, b = 238, 255   # 232, 255
    w = b - a
    offset = x*w
    offset = int(round(offset))
    return str(fabulous.color.fg256(a + offset, c))


from skid.pdfhacks.pdfmill import gs, template, Context
def main():

    outdir = 'tmp'
    outfile = outdir + '/output.html'

    pages = []
    for i, (meta, d, pdf) in enumerate(data()):

        if i >= 1:
            break

        if find_authors(meta, d, pdf):

            gs(meta['cached'], outdir)
            pages.append(pdf.pages[0])


    # if we want to draw the first pages of many pdfs on one html document we
    # have to lie to the items -- tell them they are on pages other than the
    # first...
    yoffset = 0
    for p in pages:
        for item in p.items:
            if hasattr(item, 'yoffset'):
                item.yoffset += yoffset
        yoffset += p.height

    with file(outfile, 'wb') as f:
        template.render_context(Context(f, pages=pages))

    import webbrowser
    webbrowser.open(outfile)


def tovector(x):
    for k, v in x.attributes.items():
        if k == 'author':
            continue
        if isinstance(v, (bool, basestring)):
            yield '%s=%s' % (k,v)


if __name__ == '__main__':
    main()
