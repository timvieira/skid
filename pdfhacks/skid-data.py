import re
import fabulous

from skid.add import Document
from skid.config import CACHE
from skid.pdfhacks.pdfmill import convert, gs, template, Context

from arsenal.iterextras import iterview
from arsenal.terminal import red, green, yellow, blue, magenta


def data():

    for filename in CACHE.glob('*.pdf'):

        d = Document(filename)
        meta = d.parse_notes()

        if meta.get(u'author', None):

            ff = ' file://' + filename
            print
            print red % ('#' + '_' *len(ff))
            print red % ('#' + ff)
            print
            print ('%s: %s' % (yellow % 'meta', meta.get(u'title', None))).encode('utf8')
            print ('%s: %s' % (yellow % 'meta', meta.get(u'author', None))).encode('utf8')
            print

            pdf = convert(filename)

            yield (meta, d, pdf)


def shingle(x, size=3):
    """
    >>> shingle("abcdef", size=3)
    ['abc', 'bcd', 'cde', 'def']
    """
    return [x[i:i + size] for i in xrange(0, len(x) - size + 1)]


def find_authors(meta, d, pdf):

    #print meta['title']
    #print meta['author'].encode('utf8')

    lines = []

    author = d.parse_notes()['author']
    authors = [set(shingle(x.strip())) for x in author.split(';')]

    if not pdf:
        return

    items = pdf.pages[0].items

    for x in items:

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

        lines.append(((distance, -x.attributes['fontsize']), x))

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

    font_name = lines[0][1].attributes.get('fontname', None)
    font_size = lines[0][1].attributes.get('fontsize', None)

    extracted = []

    for (distance, _), item in lines[:10]:  # most similar lines

        x = item.attributes
        print '  %6.4f' % distance,

        text = x['text'].encode('utf8')

        info = x.copy()
        info.pop('text')

        if x['fontname'] == font_name and x['fontsize'] == font_size:
            print green % text, info
            x['author'] = True
            extracted.append(text)

        else:
            print red % text, info


    # dump training data to file.
    with file('data.tsv', 'a') as f:
        for item in items:
            f.write(str(item.attributes.get('author', False)))
            f.write('\t')
            f.write('alwayson')
            f.write('\t')
            f.write('\t'.join(tovector(item)))
            f.write('\n')

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


def color(c, x):
    "Colorize numbers in [0,1] based on value; darker means smaller value."
    a, b = 238, 255   # 232, 255
    w = b - a
    offset = x*w
    offset = int(round(offset))
    return str(fabulous.color.fg256(a + offset, c))


from learn import predict, pickle

def main():

    outdir = 'tmp'
    outfile = outdir + '/output.html'

    # create file, we'll be appending to it as we go along
    with file('data.tsv', 'wb') as f:
        f.write('')

    with file('weights.pkl~') as f:
        w = pickle.load(f)

    pages = []
    for i, (meta, d, pdf) in enumerate(data()):
#        if i >= 10:
#            break
        if find_authors(meta, d, pdf):
            gs(meta['cached'], outdir)
            pages.append(pdf.pages[0])

            for x in pdf.pages[0].items:
                if predict(w, {k: 1.0 for k in tovector(x)}) == 'True':
                    x.style['border'] = '2px solid red'
                    print '%s: %s' % (magenta % 'author', x.text)


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
            yield ('%s=%s' % (k,v)).replace('\n','').replace('\t','').encode('utf8')


if __name__ == '__main__':
    main()
