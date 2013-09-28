"""
Get training data for metadata extraction based on user notes.

Applies various hueristics because annotation is technically "out of band",
whereas most machine learning techniques require "in band" annotation. In our
case this means we want to know which boxes or chunks of text gave rise to the
annotation.

This is slighly challenging because of noise in the pdf text extraction, many
possible extraction sites, spelling variation.
"""

import re
from path import path

from skid.add import Document
from skid.config import CACHE
from skid.pdfhacks.pdfmill import pdfminer, gs, template, Context

from arsenal.iterextras import iterview, islice
from arsenal.terminal import red, green, yellow, blue, magenta

from skid.pdfhacks.learn import predict, load, features
from skid.utils.misc import color, shingle


def data(verbose=True):
    """
    Get a list of skid pdfs which have authors annotated.
    """
    for filename in iterview(CACHE.glob('*.pdf')):
        d = Document(filename)
        meta = d.parse_notes()
        if meta['author']:
            if verbose:
                ff = ' file://' + filename
                print
                print red % ('#' + '_' *len(ff))
                print red % ('#' + ff)
                print
                print ('%s: %s' % (yellow % 'meta', meta['title'])).encode('utf8')
                print ('%s: %s' % (yellow % 'meta', ' ; '.join(meta['author']))).encode('utf8')
                print
            yield (meta, d, pdfminer(filename))


def find_authors(meta, d, pdf, output):

    authors = [set(shingle(x.strip())) for x in meta['author']]
    author = ' ; '.join(meta['author'])

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

        text = x.text
        text = re.sub(',', ' ', text)
        text = text.encode('utf8', 'ignore')  # HACK: ignores non-ascii

        b = shingle(text)
        b = set(b)

        if not b:
            continue

        dist = -len(T & b) * 1.0 / len(T | b)

        if dist <= -0.1:
            title_candidates.append(((dist, -x.fontsize), x))

        distance = sum(-len(a & b) * 1.0 / len(a | b) for a in authors)

        if distance > -0.2:
            continue

        author_candidates.append(((distance, -x.fontsize), x))

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
        x.style['background-color'] = 'rgba(0,255,0,0.2)'

    # dump training data to file.
    with file(output, 'a') as f:
        for item in items:
            f.write(item.attributes['label'])
            f.write('\t')
            f.write('alwayson')
            f.write('\t')
            f.write('\t'.join(features(item)))
            f.write('\n')

    print

    return True


def heuristic(target, candidates):
    """
    Applies string overlap with ``target`` heuristic to ``candidates``.

    Used to winnow the collection of candidates.
    """

    extracted = []
    candidates.sort()

    # font name and size of top hit
    fontname = candidates[0][1].fontname
    fontsize = candidates[0][1].fontsize

    print
    print 'Candidates:'
    for (distance, _), item in candidates[:10]:  # most similar lines
        x = item.attributes
        print '  %6.4f' % distance,

        text = item.text.encode('utf8')
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

    size = 3
    c = set(shingle(extracted_text, n=size))

    tally = [0]*len(target)
    for i in xrange(len(target)):
        if target[i:i+size] in c:
            for j in xrange(i, i+size):
                tally[j] += 1

    print ''.join(color(c, 1 - x*1.0/3) for c, x in zip(target, tally))

    return extracted


outdir = path('tmp')              # html output and cached ghostscript images to here
outfile = outdir / 'output.html'

def main(output='data.tsv'):
    """
    Build data set from user annotation.

    Outputs data.tsv

    """

    # create file, we'll be appending to it as we go along
    with file(output, 'wb') as f:
        f.write('')

    try:
        w = load('weights.pkl~')
    except IOError:
        print 'failed to load file'
        w = None

    pages = []
    for meta, d, pdf in islice(data(), None):
        if find_authors(meta, d, pdf, output):
            gs(meta['cached'], outdir)
            pages.append(pdf.pages[0])

            if w is not None:
                for x in pdf.pages[0].items:
                    y = predict(w, {k: 1.0 for k in features(x)})
                    if y != 'other':
                        x.style['border'] = '2px solid %s' % {'author': 'green', 'title': 'blue'}[y]
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


def markup_pdf(filename):
    """
    Apply learned model on a pdf.

    Creates a image of the first page.
    """

    try:
        w = load('weights.pkl~')
    except IOError:
        print 'failed to load file'
        w = None

    pages = []

    filename = path(filename)

    pdf = pdfminer(filename)

    gs(filename, outdir)
    pages.append(pdf.pages[0])

    if w is not None:
        for x in pdf.pages[0].items:
            y = predict(w, {k: 1.0 for k in features(x)})
            if y != 'other':
                x.style['border'] = '2px solid %s' % {'author': 'magenta', 'title': 'blue'}[y]
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
    webbrowser.open(f.name)


if __name__ == '__main__':
    from arsenal.automain import automain
    automain(available=[markup_pdf, main])
    #main()
