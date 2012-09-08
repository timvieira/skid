#!/usr/bin/env python
from __future__ import division

import re, os
from glob import glob
from collections import defaultdict, Counter

import numpy as np
from numpy import dot, sqrt, zeros, log

import pylab as pl
import matplotlib as mpl
from pylab import show, scatter, ion, grid, subplot, imshow
from pandas import DataFrame

#import matplotlib.image

from viz import pointbrowser, lasso
from iterextras import iterview
from debug import ip
from viz.mds import mds


class Browser(lasso.LassoBrowser): #(pointbrowser.PointBrowser):

    def __init__(self, X, **kwargs):
        self.circle = None
        super(Browser, self).__init__(X, callback=self._callback, **kwargs)

    def onpress(self, event):
        if self.selected is not None and len(self.selected):
            for idx in self.selected:
                row = self.df.ix[idx]
                obj = row['obj']
                if event.key == 'f':
                    pdf = obj.pdf_file
                    os.system('evince %s 2>/dev/null &' % pdf)
                if event.key == 't':
                    os.system('gedit %s &' % obj.text_file)
                if event.key == 'd':
                    print
                    print '----'
                    print file(obj.outdir + '/notes.org').read()
                    print '----'

        super(Browser, self).onpress(event)

    def _callback(self, m):
        if m.empty:
            return
        print '***********************************'
        common_words = reduce(set.intersection, m['obj'].map(lambda x: x.features))
        print common_words
        print '***********************************'


class Document(object):

    def __init__(self, i, filename):
        self.id = i
        self.filename = filename

        self.text_file = filename
        self.pdf_file = filename.replace('.d/data/text', '')
        self.outdir = filename.replace('/data/text', '')

        self.words = [w.lower() for w in re.findall('[A-Za-z]+', file(filename).read()) if 3 < len(w) < 20]
        self.setofwords = set(self.words)

        self.features = self.setofwords

        tf = Counter(self.words)
        z = sum(tf.values())
        self.tf = {w: tf[w]/z for w in tf}

        self.tfidf = self.norm = None

    def jaccard(self, other):
        "Jaccard distance"
        A = self.setofwords
        B = other.setofwords
        z = len(A | B)
        if z == 0: return 1.0
        return 1 - len(A & B) * 1.0 / z

    def compute_tfidf(self, df):
        tfidf = self.tfidf = defaultdict(float)
        tf = self.tf
        for t in self.setofwords:
            tfidf[t] = tf[t] * -log(df[t])
        self.norm = sqrt(sum(x*x for x in tfidf.itervalues()))

    def tfidf_distance(self, other):
        a = self.tfidf
        b = other.tfidf
        d = sum(a[term] * b[term] for term in a)
        return 1 - d * 1.0 / (self.norm * other.norm)


# TODO: use Whoosh to retrieve documents, use tf-idf score it has already
# computed.
def compute_similarities(documents, threshold=0.9):

    N = len(documents)
    print 'build tf and idf tables...',
    # map from words to documents containing word
    index = defaultdict(set)
    for d in documents:
        for w in d.words:
            index[w].add(d)
    # document frequency
    df = {w: len(index[w])*1.0/N for w in index}
    for d in documents:
        d.compute_tfidf(df)
    print 'done.'

    # cached file to document object
    z = {d.pdf_file: d for d in documents}

    seeds = documents

    dd = []
    ddocs = set()

    print 'retrieval...'
    from skid.index import DIRECTORY, NAME, open_dir
    ix = open_dir(DIRECTORY, NAME)
    with ix.searcher() as searcher:
        for doc in iterview(seeds):

            result = searcher.find('cached', unicode(doc.pdf_file))

            if not result:
                print
                print '[ERROR] document not found', doc.pdf_file
                continue

            if len(result) > 1:
                print '[WARN] multiple results cached in the same place', doc.pdf_file

            result = result[0]

            for hit in result.more_like_this(top=50, numterms=5, fieldname='text'):
                attrs = hit.fields()

                try:
                    hitdoc = z[attrs['cached']]
                except KeyError:
                    print 'skip due to key error:', attrs['cached']
                    continue
                else:
                    dd.append((doc, hitdoc))
                    ddocs.add(doc.id)
                    ddocs.add(hitdoc.id)


    print 'done.'

    N = max(ddocs)
    m = zeros((N,N))

    toohigh = 0
    n_nans = 0
    m = zeros((N, N))

    for (a,b) in dd:
        if a.id < b.id:
            dist = a.tfidf_distance(b)
            if np.isnan(dist):
                n_nans += 1
                dist = 1     # max distance
            if dist < threshold:
                m[a.id, b.id] = m[b.id, a.id] = dist
            else:
                toohigh += 1
    print 'too high: %s (NaNs: %s)' % (toohigh, n_nans)
    print 'total', len(documents)*(len(documents)-1)/2

    return m


def main(documents):
    "Start interactive 2-dimensional representation of documents."

    documents = [Document(i, f) for i, f in enumerate(documents)]
    m = compute_similarities(documents)
    Y, _ = mds(m)

    X = []
    for d in documents:

        if d.id >= Y.shape[0]:
            print 'skipping:', d.id
            continue

        X.append({'id': d.id,
                  'filename': d.filename,
                  'obj': d,
                  'x': Y[d.id,0],
                  'y': Y[d.id,1]})

#    for i in xrange(len(documents)):
#        for j in xrange(i + 1, len(documents)):
#            x = Y[[i,j], 0]
#            y = Y[[i,j], 1]
#            pl.plot(x, y, lw=0.2*m[i,j], alpha=m[i,j], c='k')

    X = DataFrame(X)
    sct = scatter(X['x'], X['y'], s=20, c='b', marker='o', alpha=0.3)

    b = Browser(X, ax=sct.get_axes())
#    b = PointBrowser(X, ax=sct.get_axes())

#    b.ax.figure.set_facecolor('white')
#    b.ax.set_axis_off()

    show()
    #ip()


if __name__ == '__main__':
    from skid.config import CACHE
    main(glob(CACHE + '/*.pdf.d/data/text'))
