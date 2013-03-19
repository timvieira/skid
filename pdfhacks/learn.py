from __future__ import division
import sys, cPickle as pickle
from collections import defaultdict, Counter
from arsenal.terminal import red, green, magenta
from arsenal.nlp.evaluation import F1


def load(filename):
    with file(filename) as f:
        for line in f:
            line = line.strip().split('\t')
            label = line[0]
            features = line[1:]
#            yield label, conjunctions(features)
            yield label, features

def conjunctions(phi):
    return ['(%s & %s)' % (phi[i], phi[j]) for i in xrange(len(phi)) for j in xrange(i+1)]

def freq_filter(data, c, threshold=3):
    for y, phi in data:
        yield y, [k for k in phi if c[k] >= threshold]

def feature_label_freq_filter(data, c, threshold=3):
    for y, phi in data:
        yield y, [k for k in phi if c[y, k] >= threshold]

def traintest(datafile):
    data = list(load(datafile))
    n = len(data)
    a = data[:int(n *0.7)]
    b = data[int(n *0.7):]

    # feature count filter
    c = Counter(k for _, phi in data for k in phi)
    a = freq_filter(a, c)

    c = Counter((y, k) for y, phi in data for k in phi)
    a = feature_label_freq_filter(a, c)

    return list(a), b

#_________
# learning

def scores(w, phi):
    return {y: sum(w[y][k] for k in phi) for y in w}

def predict(w, phi):
    return argmaxd(scores(w, phi))

def argmaxd(x):
    return max(zip(x.values(), x.keys()))[1]

def learn(data):
    labels = {label for label, _ in data}
    w = {y: defaultdict(float) for y in labels}
    for t in xrange(50):
        alpha = 10.0 / (t + 1)**0.8
        for label, features in data:
            y = predict(w, features)
            if label != y:
                for k in features:
                    w[label][k] += alpha
                    w[y][k] -= alpha
    return w

def save(weights, filename):
    with file(filename, 'wb') as f:
        pickle.dump(weights, f)

# ___________________
# error analysis

def f1(name, data, w):
    print
    print name
    f = F1()
    for (i, (target, phi)) in enumerate(data):
        f.report(i, predict(w, phi), target)
    f.scores()

def errors(name, data, w):
    print
    print 'ERRORS:', name
    for target, phi in data:
        y = predict(w, phi)
        if y == target:
            pass
        else:
            print ' ', green % '%-6s' % target, red % '%-6s' % y, phi

            l = target
            print '   ', ' '.join('%s%s' % (k, magenta % '(%g)' % w) for _, w, k in sorted([(-abs(w[l][k]), w[l][k], k) for k in phi]))

            l = y
            print '   ', ' '.join('%s%s' % (k, magenta % '(%g)' % w) for _, w, k in sorted([(-abs(w[l][k]), w[l][k], k) for k in phi]))



def main():
    datafile = sys.argv[1]

    train, test = traintest(datafile)
    print 'train: %s, test: %s' % (len(train), len(test))

    w = learn(train)
    save(w, 'weights.pkl~')

    f1('train', train, w)
    f1('test', test, w)

    errors('train', train, w)
    errors('test', test, w)

    for _, w, label, k in sorted([(abs(w[y][k]), w[y][k], y, k) for y in w for k in w[y] if w[y][k] != 0.0]):
        if w > 0:
            print '%8g  %5s  %s' % (w, label, k)


if __name__ == '__main__':
    main()
