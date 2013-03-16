import cPickle as pickle
from skid.add import Document
from skid.pdfhacks.pdfmill import convert
from arsenal.iterextras import iterview
from arsenal.terminal import red, green
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

            try:
                pdf = convert(filename)
            except:
                if debug:
                    print red % 'FAIL', filename
                continue

            try:
                pickle.dumps(pdf)
            except:
                if debug:
                    print red % 'bad file.', filename
                continue

            yield (meta, d, pdf)


def build_data():
    docs = list(data())
    # save the file every time...
    with file('skid-data.pkl~', 'wb') as f:
        pickle.dump(docs, f)


def load():
    with file('skid-data.pkl~') as f:
        return pickle.load(f)


import re
import jellyfish
from jellyfish import levenshtein_distance


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

    a = set(shingle(author.replace(';', '')))

    for x in pdf.items[0]:

        text = x.attributes['text']
        text = re.sub(',', ' ', text)

        # remove lower case words
        # TODO: there are some exceptions like 'de Martins'
#        text = re.sub('\\b[a-z]\S*\\b', '', text)
#        text = re.sub('\s\s+', ' ', text)

        text = text.encode('utf8', 'ignore')  # HACK: ignores non-ascii

#        print
#        print x.attributes['text']
#        print text

#        distance = levenshtein_distance(authors, text)

        b = shingle(x.attributes['text'])
        b = set(b)

        if not b:
            continue

        distance = -len(a & b) * 1.0 / len(a | b)

        if distance > -0.11:
            continue

        if distance >= 0:
            continue

        lines.append(((distance, -x.attributes['font-size']), x.attributes))

    # ERRORS:
    #  - copyright
    #  - emails
    #  - citations
    #  - sometimes author have same font, but different fontsize (even though it
    #    looks the same size in the pdf)

    # TODO:
    #  - check for n-grams explained in author string.
    #  - break-up author names. They often appear in separate bboxes

    if not lines:
        print red % 'Sorry, no lines in the document :-('
        return

    lines.sort()
    print

    font_name = lines[0][1].get('font-name', None)
    font_size = lines[0][1].get('font-size', None)


    extracted = []

    for (distance, _), x in lines[:10]:  # most similar lines

        print '  %6.4f' % distance,

        text = x.pop('text').encode('utf8')

        if x['font-name'] == font_name and x['font-size'] == font_size:
            print green % text, x
            extracted.append(text)
        else:
            print red % text, x

    print


    c = reduce(set.union, map(set, map(shingle, extracted)))

    tally = [0]*len(author)
    size = 3
    for i in xrange(len(author)):
        if author[i:i+size] in c:
            for j in xrange(i, i+size):
                tally[j] += 1


    import fabulous
    def color(c, x):
        "Colorize numbers in [0,1] based on value; darker means smaller value."

        a, b = 238, 255   # 232, 255
        w = b - a
        offset = x*w
        offset = int(round(offset))
        return str(fabulous.color.fg256(a + offset, c))

    print ''.join(color(c, 1 - x*1.0/3) for c, x in zip(author, tally))


if __name__ == '__main__':
    #d, pdf = data_iter.next()

    for xx in data():
        find_authors(*xx)

    # TODO: missing 'leon bottou' and 'jonas peters'


#    build_data()
