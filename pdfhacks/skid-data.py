import cPickle as pickle
from path import path
from skid.add import Document
from skid.pdfhacks.pdfmill import convert
from arsenal.iterextras import iterview
from arsenal.terminal import red

def build_data():

    docs = []
    for filename in iterview(path('/home/timv/.skid/marks/').glob('*.pdf')):

        d = Document(filename)
        meta = d.parse_notes()
        if meta.get(u'author', None):
            print
            print meta.get(u'title', None)
            print meta.get(u'author', None)
            print

            try:
                pdf = convert(filename)
            except:
                print red % 'FAIL', filename
                continue

            try:
                pickle.dumps(pdf)
            except:
                print red % 'bad file.', filename
                continue

            docs.append((d, pdf))
            print '>>>', len(docs)

    # save the file every time...
    with file('skid-data.pkl~', 'wb') as f:
        pickle.dump(docs, f)


def load():
    with file('skid-data.pkl~') as f:
        return pickle.load(f)


if __name__ == '__main__':
    build_data()
