import re
import fabulous

from skid.add import Document
from skid.config import CACHE
from skid.pdfhacks.pdfmill import convert, gs, template, Context

from arsenal.iterextras import iterview
from arsenal.terminal import red, green, yellow, blue, magenta


def data():

    for filename in iterview(CACHE.glob('*.pdf')):

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

    author = meta['author']
    authors = [set(shingle(x.strip())) for x in author.split(';')]

    title = meta['title']
    T = set(shingle(title.strip()))

    if not pdf:
        return

    items = pdf.pages[0].items

    author_candidates = []
    title_candidates = []

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

        dist = -len(T & b) * 1.0 / len(T | b)

        if dist <= -0.1:
            title_candidates.append(((dist,
                                      -x.attributes['fontsize']), x))

        distance = sum(-len(a & b) * 1.0 / len(a | b) for a in authors)

        if distance > -0.2:
            continue

        author_candidates.append(((distance, -x.attributes['fontsize']), x))

    # ERRORS:
    #  - copyright
    #  - emails
    #  - citations
    #  - sometimes author have same font, but different fontsize (even though it
    #    looks the same size in the pdf)

    # TODO:
    #  - check for n-grams explained in author string.

    if not author_candidates or not title_candidates:
        print red % 'Sorry, no lines in the document :-('
        return

    for x in items:
        x.attributes['label'] = 'other'

    for x in heuristic(title, title_candidates):
        x.attributes['label'] = 'title'
        x.style['background-color'] = 'rgba(0,0,255,0.2)'

    for x in heuristic(author, author_candidates):
        x.attributes['label'] = 'author'
        x.style['background-color'] = 'rgba(255,0,0,0.2)'

    # dump training data to file.
    with file('data.tsv', 'a') as f:
        for item in items:
            f.write(item.attributes['label'])
            f.write('\t')
            f.write('alwayson')
            f.write('\t')
            f.write('\t'.join(tovector(item)))
            f.write('\n')

    print

    return True


def heuristic(target, candidates):
    extracted = []
    candidates.sort()

    # font name and size of top hit
    fontname = candidates[0][1].attributes.get('fontname', None)
    fontsize = candidates[0][1].attributes.get('fontsize', None)

    print
    print 'Candidates:'
    for (distance, _), item in candidates[:10]:  # most similar lines
        x = item.attributes
        print '  %6.4f' % distance,

        text = x['text'].encode('utf8')
        info = x.copy()
        info.pop('text')

        if item.fontname == fontname and item.fontsize == fontsize:
            print green % text, info
            extracted.append(item)
        else:
            print red % text, info

    if not extracted:
        print red % 'failed to extract anything relevant :-('
        return

    extracted_text = ' '.join(x.text for x in extracted).encode('utf8')

    c = set(shingle(extracted_text))

    tally = [0]*len(target)
    size = 3
    for i in xrange(len(target)):
        if target[i:i+size] in c:
            for j in xrange(i, i+size):
                tally[j] += 1

    print ''.join(color(c, 1 - x*1.0/3) for c, x in zip(target, tally))

    return extracted


def color(c, x):
    "Colorize numbers in [0,1] based on value; darker means smaller value."
    a, b = 238, 255   # 232, 255
    w = b - a
    offset = x*w
    offset = int(round(offset))
    return unicode(fabulous.color.fg256(a + offset, c)).encode('utf8')


from skid.pdfhacks.learn import predict, pickle

def main():

    outdir = 'tmp'
    outfile = outdir + '/output.html'

    # create file, we'll be appending to it as we go along
    with file('data.tsv', 'wb') as f:
        f.write('')

    with file('weights.pkl~') as f:
        w = pickle.load(f)

    pages = []
    for meta, d, pdf in data():
        if find_authors(meta, d, pdf):
            gs(meta['cached'], outdir)
            pages.append(pdf.pages[0])

            for x in pdf.pages[0].items:
                y = predict(w, {k: 1.0 for k in tovector(x)})
                if y != 'other':
                    x.style['border'] = '2px solid %s' % {'author': 'red', 'title': 'blue'}[y]

                    c = {'author': magenta, 'title': blue}[y]
                    print '%s: %s' % (c % y, x.text)

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

        if k == 'label':
            continue

        if isinstance(v, (bool, basestring, int)):
            yield ('%s=%s' % (k,v)).replace('\n','').replace('\t','').encode('utf8')

        elif isinstance(v, list):
            for x in v:
                yield ('%s=%s' % (k,x)).replace('\n','').replace('\t','').encode('utf8')

        else:
            assert False, (k,v)


if __name__ == '__main__':
    main()
