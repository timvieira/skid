
import sys, pickle as pickle
from collections import defaultdict, Counter
from arsenal.terminal import colors
from arsenal.nlp.evaluation import F1
from arsenal.iterextras import iterview

def features(x):
    "Features used for learning and inference."
#    return conjunctions(attributes(x))
    return attributes(x)

def attributes(x):
    "Vector of active boolean attributes. Note these aren't features yet. Use features for that."
    for k, v in list(x.attributes.items()):
        if k == 'label':
            continue
        if isinstance(v, (bool, str, int)):
            yield ('%s=%s' % (k,v)).replace('\n','').replace('\t','').encode('utf8')
        elif isinstance(v, list):
            for x in v:
                yield ('%s=%s' % (k,x)).replace('\n','').replace('\t','').encode('utf8')
        else:
            assert False, (k,v)


class Instance(object):
    def __init__(self, label, attributes):
        self.attributes = attributes
        self.label = label
        self.features = None

def load_data(filename):
    with open(filename) as f:
        for line in f:
            line = line.strip().split('\t')
            label = line[0]
            features = line[1:]
            yield Instance(label, features)

def conjunctions(phi):
    phi = list(phi)
    return ['(%s & %s)' % (phi[i], phi[j]) for i in range(len(phi)) for j in range(i+1)]

def freq_filter(data, c, threshold=5):
    for x in data:
        x.features = [k for k in x.features if c[k] >= threshold]

def feature_label_freq_filter(data, c, threshold=5):
    for x in iterview(data, every=int(len(data)*.1)):
        y = x.label
        x.features = [k for k in x.features if c[y, k] >= threshold]

def traintest(datafile):
    data = list(load_data(datafile))
    n = len(data)

    p = 0.7
    a = data[:int(n * p)]
    b = data[int(n * p):]

    for x in data:
        x.features = [k for k in x.attributes if k.split('=')[0] not in {'text', 'word', 'x0', 'y0', 'x1', 'y1', 'height', 'width'}]

    # feature count filter
#    c = Counter(k for x in data for k in x.features)
#    freq_filter(a, c)

#    c = Counter((x.label, k) for x in data for k in x.features)
#    feature_label_freq_filter(a, c, threshold=5)

#    print 'conjunctions..'
#    for x in iterview(data):
#        x.features = conjunctions(x.features)

#    print 'filter conjunctions...'
#    c = Counter((x.label, k) for x in data for k in x.features)
#    feature_label_freq_filter(a, c, threshold=3)

    return list(a), b

#_________
# learning

def scores(w, phi):
    return {y: sum(w[y][k] for k in phi) for y in w}

def predict(w, phi):
    return argmaxd(scores(w, phi))

def argmaxd(x):
    return max(list(zip(list(x.values()), list(x.keys()))))[1]

def learn(data, test):
    labels = {x.label for x in data}
    w = {y: defaultdict(float) for y in labels}
    for t in iterview(range(10), every=1):

#        print
#        print
#        print 'Iteration', t

        alpha = 10.0 / (t + 1)**0.8
        for x in data:
            y = predict(w, x.features)
            if x.label != y:
                for k in x.features:
                    w[x.label][k] += alpha
                    w[y][k] -= alpha

#        f1('train', data, w)
#        f1('test', test, w)

    return w

def save(weights, filename):
    with open(filename, 'wb') as f:
        pickle.dump(weights, f)

def load(filename):
    with open(filename) as f:
        return pickle.load(f)

# ___________________
# error analysis

def f1(name, data, w):
    print()
    print(name)
    f = F1()
    for (i, x) in enumerate(data):
        f.report(i, predict(w, x.features), x.label)
    f.scores()


def errors(name, data, w):
    print()
    print('ERRORS:', name)
    for x in data:
        y = predict(w, x.features)
        if y == x.label:
            pass
        else:
            print(' ', colors.green % '%-6s' % x.label, colors.red % '%-6s' % y, [k for k in x.attributes if k.startswith('text')]) #x.features
            l = x.label
            print('   ', ' '.join('%s%s' % (k, colors.magenta % '(%g)' % w) for _, w, k in sorted([(-abs(w[l][k]), w[l][k], k) for k in x.features])))
            l = y
            print('   ', ' '.join('%s%s' % (k, colors.magenta % '(%g)' % w) for _, w, k in sorted([(-abs(w[l][k]), w[l][k], k) for k in x.features])))


def main():
    datafile = sys.argv[1]

    train, test = traintest(datafile)
    print('train: %s, test: %s' % (len(train), len(test)))


    from scipy.sparse import dok_matrix
    from sklearn import linear_model
    from sklearn.svm import SVC
    from arsenal.alphabet import Alphabet

    N_FEATURES = 100000

    alphabet = Alphabet(random_int=N_FEATURES)

    def _f1(name, data, c, verbose=True):
        if verbose:
            print()
            print(name)
        f = F1()
        for (i, x) in enumerate(data):

            phi = dok_matrix((1, N_FEATURES))
            for k in x.features:
                phi[0, alphabet[k] % N_FEATURES] = 1.0

            [y] = c.predict(phi)
            f.report(i, y, x.label)
        f.scores(verbose=verbose)
        return f

    X = dok_matrix((len(train), N_FEATURES))

    M = len(train)

    Y = []
    X = dok_matrix((M, N_FEATURES))
    for i, x in enumerate(train):
        # binary features
        for k in x.features:
            X[i, alphabet[k] % N_FEATURES] = 1.0
        Y.append(x.label)
    X = X.tocsc()


    c = SVC(class_weight={'author': 1000,
                          'title': 1000,
                          'other': 1.0},
            verbose=1)

    c.fit(X, Y)

    _f1('train', train, c)
    ff = _f1('test', test, c, verbose=1)

    if 0:
        import numpy as np
        import matplotlib.pyplot as pl
        from mpl_toolkits.mplot3d import Axes3D
        ax = pl.figure().add_subplot(111, projection='3d')

        pl.ion()

        data = []

        for (author_weight, title_weight) in iterview(np.random.uniform(1, 10, size=(100, 2))):
            print()
            print('params:', (author_weight, title_weight))

            c = SVC(class_weight={'author': author_weight,
                                  'title': title_weight,
                                  'other': 1.0},
                    verbose=1)

            #c = linear_model.SGDClassifier()
            c.fit(X, Y)

            #_f1('train', train, c)
            ff = _f1('test', test, c, verbose=1)

            score = sum(x for (_, _, _, _, x) in ff.scores(verbose=0))

            data.append((author_weight, title_weight, score))
            print('score:', score)

            x,y,z=list(zip(*data))
            ax.clear()
            ax.scatter(x,y,z)
            ax.figure.canvas.draw()

        print('done')
        pl.ioff()
        pl.show()

    #w = learn(train, test)
    #save(w, 'weights.pkl~')

    #f1('train', train, w)
    #f1('test', test, w)

    #if 0:
    #    errors('train', train, w)
    #    errors('test', test, w)

    #if 0:
    #    for _, w, label, k in sorted([(abs(w[y][k]), w[y][k], y, k) for y in w for k in w[y] if w[y][k] != 0.0]):
    #        if w > 0:
    #            print '%8g  %5s  %s' % (w, label, k)


if __name__ == '__main__':
    main()
