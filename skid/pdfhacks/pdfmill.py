#!/usr/bin/env python
"""
Heuristic title extractor.

There is also a bunch of junk in here to visualize the output of
pdfminer. Eventually, this will amount to a feature development/debugger for a
machine learning information extraction system for processing your pdfs. For
now, you'll just have to settle with this mess.

TODO: pdfminer often doesn't recognize a font and reports a bogus line
height. There is a quick heuristic to fix this using the observation that
text-line bounding boxes shouldn't overlap. Thus a line is at most as tall as
the bottom of the lowest box above it.

"""

import re, os, sys, pprint, urllib
from collections import Counter
from pandas import DataFrame

from arsenal.iterextras import groupby2
from arsenal.text.utils import remove_ligatures
from arsenal.misc import ignore_error
from arsenal.debug import ip
from arsenal.terminal import red, green, blue, yellow

from skid.pdfhacks.conversion import pdf2image

# pdfminer
from pdfminer.layout import LAParams, LTPage, LTTextLine
from pdfminer.pdfparser import PDFParser, PDFDocument, PDFSyntaxError
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator

try:
    # mako for html output template
    from mako.template import Template
    from mako.runtime import Context
except ImportError:
    def Template(*args):
        return

run_feature_extraction = 1

if run_feature_extraction:
    from skid.pdfhacks import features

# TODO: post/pre-processing
#
#  - remove superscript thingies from authors with a filter on char objects on
#    textline!


# TODO: features
#
#  - rank of fontsize (= bbox height)
#
#  - presence/freq of comma, and, single initial
#
#  - position on page
#
#  - bbox width (relative, rank)
#
#  - email, university, institute, address patterns
#
#  - letter patterns, word pattern (not entire line pattern)
#
#  - nearest box underneath what looks like a title (according to simple title
#    extraction heuristic)
#
#  - above the word 'abstract' (and below title guess)
#
#  - (90% of authors should be retrieved by taking words between abstract and
#    title. which are not emails, urls, addresses, or institution names)
#
#  - copyright typically lists author name (but, might be an institution?)
#

def feature_extraction(item):

    text = item.text

    if not text:
        return

    item.attributes.update({
        'x0': item.x0, 'y0': item.y0, 'x1': item.x1, 'y1': item.y1,
        'width': item.width, 'height': item.height,
        'text': text,
    })

    item.attributes['fontsize'] = item.fontsize
    item.attributes['fontname'] = item.fontname

    item.attributes['abstract'] = item.abstract

    if not run_feature_extraction:
        return

    pattern = features.letter_pattern(text)

    item.attributes.update({
        'word': re.findall('(\w+|\W+)', text),
        'word-patterns': pattern.split(),
        'ends-with-hyphen': text.endswith('-'),
        'is_university': features.is_university(text),
        'title_shaped':  features.title_shaped(text),
        'letter_pattern': pattern,
        'url': features.url(text),
        'email': features.email(text),
    })


class MyItem(object):

    def __init__(self, item):
        assert not hasattr(item, 'attributes')
        self._item = item
        self.text = re.sub('[^\x20-\x7E]', '', remove_ligatures(unicode(item.get_text()).strip())).encode('utf8')
        self.yoffset = item.yoffset

        self.x0 = item.x0
        self.x1 = item.x1
        self.y0 = item.y0
        self.y1 = item.y0 + item.height  # item.y1 is often unreliable
        assert self.x0 <= self.x1 and self.y0 <= self.y1

        self.height = item.height
        self.width = item.width

        self.style = {}
        self.attributes = {}

        self.abstract = bool(re.findall('^abstract', self.text, flags=re.I))

        self.fontsize = int(item.height)
        self.fontname = 'unknown'

        self.children = [c for c in item if hasattr(c, 'fontname')]
        if self.children:
            # Use height of the character bbox as font size, which might be better
            # because it invariant to font type (but can be worse if it's
            # incorrectly reported by pdfminer).

            # take most frequent font name and size
            self.fontsize = Counter(int(c.height) for c in self.children).most_common()[0][0]
            self.fontname = Counter(c.fontname for c in self.children).most_common()[0][0]

    def render_style(self):
        sty = self.style
        return ' '.join('%s: %s;' % x for x in sty.items())

    @property
    def tooltip(self):
        return '<pre>' + urllib.quote(pprint.pformat(self.attributes)) + '</pre>'


def gs(f, outdir):
    # where we'll put the images
    imgdir = os.path.abspath(outdir) + '/img'
    fmt = os.path.basename(f) + '-page-%d.png'

    p = imgdir + '/' + (fmt % 1)

    if not os.path.exists(p):
        print >> sys.stderr, '[ghostscript]', f, '->', p
        pdf2image(f, outputdir_fmt=imgdir, output_format=fmt,
                  moreopts='-dFirstPage=1 -dLastPage=1')


def pdfminer(f):

    fp = open(f, 'rb')
    parser = PDFParser(fp)
    doc = PDFDocument()
    parser.set_document(doc)
    try:
        doc.set_parser(parser)
    except PDFSyntaxError:
        return

    rsrcmgr = PDFResourceManager()

    c = HTMLConverter(os.path.basename(f))

    laparams = LAParams(all_texts=True)

    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    for page in doc.get_pages():
        worked = False
#        with ignore_error():
        try:
            interpreter.process_page(page)
            worked = True
        except AssertionError:
            pass

        if not worked:
            return
        layout = device.get_result()
        c.current_page = page
        c.render(layout)
        break  # stop after first page.

    c.add_features()

    return c


class HTMLConverter(object):

    def __init__(self, filename):
        self.filename = filename
        self.yoffset = 0
        self.pages = []
        self.items = []
        self.current_page = None

    def data_frame(self):
        items = self.pages[0].items
        for x in items:
            x.attributes['obj'] = x
        return DataFrame([x.attributes for x in items])

    def play(self):

        df = self.data_frame()
        df1 = df.set_index(['fontsize', 'fontname']).sort(ascending=False)

        for k,v in df.groupby(['fontsize', 'fontname'], sort=True):
            print '-----'
            print unicode(k).encode('utf8'), unicode(v).encode('utf8')

        print df1.to_string()

        from arsenal.debug import ip; ip()

    def add_features(self):

        items = self.pages[0].items

        # above/below abstract
        abstracts = [x for x in items if x.abstract]
        if len(abstracts) == 1:
            [abstract] = abstracts
            for x in items:
                x.attributes['above-abstract'] = x.yoffset < abstract.yoffset
        else:
            # TODO: handle no abstracts or many abstracts
            pass

        # extract local features
        for page in self.pages:
            for x in page.items:
                feature_extraction(x)

        # fontsize frequency
        fontsize = Counter(x.fontsize for x in items)
        freq = zip(fontsize.values(), fontsize.keys())
        freq.sort(reverse=True)
        rank = {k: rank + 1 for rank, (v, k) in enumerate(freq)}
        for x in items:
            x.attributes['fontsize-freq-rank'] = rank[x.fontsize]

        # width frequency
        w = Counter(int(x.width) for x in items)
        freq = zip(w.values(), w.keys())
        freq.sort(reverse=True)
        rank = {k: rank + 1 for rank, (v, k) in enumerate(freq)}
        for x in items:
            x.attributes['width-rank'] = rank[int(x.width)]

        # fontsize rank
        fontsize = groupby2(items, lambda x: x.fontsize)
        for rank, (_, vs) in enumerate(reversed(sorted(fontsize.items()))):
            for v in vs:
                v.attributes['fontsize-size-rank'] = rank + 1

#        g = groupby2(items, key=lambda x: x.fontsize)
#        if g:
#            for x in g[max(g)]:
#                x.attributes['title'] = True
#                print '%s: %s' % (blue % 'title', x.text)
#                x.style['background-color'] = 'rgba(0,0,255,0.2)'
#        else:
#            print g

    def draw_item(self, item):

        # bounding box canonicalization
        item.x0 = int(min(item.x0, item.x1))
        item.x1 = int(max(item.x0, item.x1))
        item.y0 = int(min(item.y0, item.y1))
        item.y1 = int(max(item.y0, item.y1))
        item.width = int(item.width)
        item.height = int(item.height)

        item.yoffset = item.y0 + item.page.yoffset

        if isinstance(item, LTTextLine):
            x = MyItem(item)
            x.style['border'] = 'thin solid orange'
            self.current_page.items.append(x)

    def render(self, item):

        if isinstance(item, LTPage):
            item.yoffset = self.yoffset
            self.yoffset += item.height

            self.pages.append(item)
            self.current_page = item
            self.current_page.items = []
            self.current_page.imgfile = '%s-page-%s.png' % (self.filename, len(self.pages))

            for child in item:
                self.render(child)

            return

        # give item reference to it's page
        item.page = self.current_page

        # apply coordinate transformation; item is currently "upside down"
        item.y0 = item.page.height - item.y0
        item.y1 = item.page.height - item.y1
        item.height = item.y0 - item.y1

        if isinstance(item, LTTextLine):
            self.draw_item(item)

        else:
            if hasattr(item, '__iter__'):
                for child in item:
                    self.render(child)


template = Template("""
<html>
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8">

<style>
  * { margin:0; padding:0; }

  .popup {
    position: absolute;
    border-style: solid;
    color: black !important;
    background-color: white !important;
    padding: 5px;
    z-index: 9000;
  }
</style>

<script type="text/javascript" language="javascript" src="../misc/prototype.js"></script>

<script type="text/javascript" language="javascript">
function add_tooltip(elem) {
    if (elem.getAttribute('tooltip')) {
        elem.onclick = function(e) {
            if (this.hasClassName('selected')) {
                this.removeClassName('selected');
            } else {
                this.addClassName('selected');
            }
            var tooltip = elem.getElementsByClassName('popup');
            if (tooltip.length > 0) {
                tooltip[0].toggle();
            } else {
                var text = unescape(this.getAttribute('tooltip'));
                var tooltip = new Element('div',{'class':'popup'});
                tooltip.update(text);
                this.appendChild(tooltip);
            }
        };
    }
}

function add_tooltips() {
    $$('div[tooltip]').each(add_tooltip);
}
</script>
</head>
<body onload="add_tooltips()">


% for page in pages:

<div style="width:${int(page.width)}px; height:${int(page.height)}px; ">

    <img src="img/${page.imgfile}" width="${page.width}" />

    % for item in page.items:
        <div style="position:absolute;
                    ${item.render_style()}
                    left: ${item.x0}px;
                    top: ${item.yoffset}px;
                    width: ${item.width}px;
                    height: ${item.height}px;"
            % if item.tooltip:
                tooltip="${item.tooltip}"
            % endif
        ></div>
    % endfor

</div>

% endfor

</body>
</html>
""")


def extract_title(filename, extra=True):

    if not isinstance(filename, basestring):
        pdf = filename
        filename = pdf.filename
    else:
        try:
            pdf = pdfminer(filename)
        except KeyboardInterrupt:
            raise
        except:
            return

    # check for skid-mark
#    if os.path.exists(filename + '.d/notes.org'):
#        from skid.add import Document
#        d = Document(filename)
#        meta = d.parse_notes()
#        print meta.get(u'title', None)
#        print meta.get(u'author', None)

    if not pdf:
        return

    page = pdf.pages[0].items

    # preprocessing
    page = [x for x in page
            # Need to find a three+ letter word begining with a capital letter to be
            # considered a candidate for author or title.
            if re.findall('[A-Z][A-Za-z][A-Za-z]+', x.text)]

    # TODO: titles tend not to have single initial, unlike names, (both title
    # and author precede the word "abstract")

    g = groupby2(page, key=lambda x: x.fontsize)

    if not g:
        return

    title = ' '.join(x.text for x in g[max(g)])

    # Clean up case if all caps
    if title.isupper():
        title = title.title()

    print yellow % title.encode('utf8')

    if extra:

        # timv: this is sort of a proxy for author extraction. If it's easy to
        # copy-paste the authors maybe we don't need to have automatic extraction.
        #
        # authors often appear in a distinguishing (infrequent) font
        g = groupby2(page, key=lambda x: x.fontname)

        freq = [(len(v), k, v) for k,v in g.iteritems()]

        freq.sort()

        for count, key, items in freq:
            print
            print red % count, green % key
            for x in items[:10]:
                print yellow % x.text.encode('utf8')

    return title


def main(filenames):

    outdir = 'tmp'
    outfile = outdir + '/output.html'

    pages = []
    for filename in filenames:

        ff = ' file://' + filename

        print
        print red % ('#' + '_' *len(ff))
        print red % ('#' + ff)
        try:
            pdf = pdfminer(filename)
        except KeyboardInterrupt:
            continue
        except:
            pdf = None
            print yellow % 'ERROR'
        else:

            print yellow % unicode(extract_title(pdf)).encode('utf8')

            gs(filename, outdir)
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


if __name__ == '__main__':

    if len(sys.argv) < 2:
        print 'usage %s <input-file>+' % sys.argv[0]
        sys.exit(1)

    main(sys.argv[1:])

#    for filename in sys.argv[1:]:
#        if os.path.isdir(filename):
#            continue
#        process_file(filename)
