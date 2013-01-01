#!/usr/bin/env python
from __future__ import division

import re, os
from glob import glob
from collections import defaultdict, Counter

import numpy as np
from numpy import sqrt, zeros, log

import pylab as pl
from pylab import show, scatter, ion
from pandas import DataFrame

from viz.interact.lasso import LassoBrowser
from viz.mds import mds

from iterextras import iterview
from debug import ip


class Browser(LassoBrowser):

    def __init__(self, X, **kwargs):
        self.circle = None
        super(Browser, self).__init__(X, callback=self._callback, **kwargs)

    def onpress(self, event):
        if self.selected is not None and len(self.selected):
            for idx in self.selected:
                row = self.df.ix[idx]
                obj = row['obj']
                if event.key == 'f':
                    pdf = obj.cached
                    os.system('gnome-open %s 2>/dev/null &' % pdf)
                if event.key == 't':
                    os.system('gedit %s &' % obj.text_file)
                if event.key == 'd':
                    print '----'
                    print file(obj.d + '/notes.org').read()
                    print

        super(Browser, self).onpress(event)

    def _callback(self, m):
        if m.empty:
            return
        print '***********************************'
        common_words = reduce(set.intersection, m['obj'].map(lambda x: x.features))
        print common_words
        print '***********************************'


import skid.add

class Document(skid.add.Document):

    def __init__(self, i, filename):
        super(Document, self).__init__(filename)

        raise NotImplementedError('TODO: cleanup use better version and take advantage of super class...')

        self.id = i
        self.filename = filename

        self.text_file = filename
        self.cached = filename.replace('.d/data/text', '')
        self.d = filename.replace('/data/text', '')

        self.words = [w.lower() for w in re.findall('[A-Za-z]+', file(filename).read()) if 3 < len(w) < 20]
        self.setofwords = set(self.words)

        self.features = self.setofwords

        tf = Counter(self.words)
        z = sum(tf.values())
        self.tf = {w: tf[w]/z for w in tf}

        self.tfidf = self.norm = None

        # XXX: parse_notes does not exist anymore
        self.tags = parse_notes(file(self.d + '/notes.org').read())['tags'].split()

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


# TODO: use Whoosh's use tf-idf score so we don't have to load all documents.
def compute_similarities(documents):

    N = len(documents)
    print 'build tf and df tables...',
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
    z = {d.cached: d for d in documents}

    seeds = documents

    dd = []
    ddocs = set()

    from skid.index import DIRECTORY, NAME, open_dir
    ix = open_dir(DIRECTORY, NAME)
    with ix.searcher() as searcher:
        for doc in iterview(seeds):

            result = searcher.find('cached', unicode(doc.cached))

            if not result:
                print
                print '[ERROR] document not found', doc.cached
                continue

            if len(result) > 1:
                print '[WARN] multiple results cached in the same place', doc.cached

            result = result[0]

            for hit in result.more_like_this(top=50, numterms=5, fieldname='text'):
                attrs = hit.fields()

                try:
                    hitdoc = z[attrs['cached']]
                except KeyError:
                    print 'SKIP hit:', attrs['cached']
                    continue
                else:
                    dd.append((doc, hitdoc))
                    ddocs.add(doc.id)
                    ddocs.add(hitdoc.id)

    N = max(ddocs) + 1

    n_nans = 0
    m = zeros((N, N))

    for (a,b) in dd:
        if a.id < b.id:
            dist = a.tfidf_distance(b)
            if np.isnan(dist):
                n_nans += 1
                dist = 1     # max distance
            m[a.id, b.id] = m[b.id, a.id] = dist

    print 'NaNs: %s; total: %s' % (n_nans, len(documents)*(len(documents)-1)/2)

    return m


def main(documents):
    "Start interactive 2-dimensional representation of documents."

    print 'loading data.'
    documents = [Document(i, f) for i, f in enumerate(iterview(documents))][:25]
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

    #b.ax.figure.set_facecolor('white'); b.ax.set_axis_off()

    ion()
    show()
    ip()


if __name__ == '__main__':
    from skid.config import CACHE
    main(glob(CACHE + '/*.pdf.d/data/text'))
