#!/usr/bin/env python
"""
Heuristics title extractor.

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
from pdfminer.pdfparser import PDFParser, PDFDocument
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
#  - font name
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

    item.attributes['fontsize'] = item.font_size
    item.attributes['fontname'] = item.font_name

    item.attributes['abstract'] = item.abstract

    if not run_feature_extraction:
        return

    layout = {
    }

    textual = {
        'ends-with-hyphen': text.endswith('-'),
        'is_university': features.is_university(text),
        'title_shaped':  features.title_shaped(text),
        'letter_pattern': features.letter_pattern(text),
        'url': features.url(text),
        'email': features.email(text),
    }

    item.attributes.update(layout)
    item.attributes.update(textual)


class MyItem(object):

    def __init__(self, item):
        assert not hasattr(item, 'attributes')
        self._item = item
        self.text = remove_ligatures(item.get_text().strip())  # cleanup text
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

        self.abstract = bool(re.findall('abstract', self.text, flags=re.I))

        self.font_size = int(item.height)
        self.font_name = 'unknown'

        self.children = [c for c in item if hasattr(c, 'fontname')]
        if self.children:
            # Use height of the character bbox as font size, which might be better
            # because it invariant to font type (but can be worse if it's
            # incorrectly reported by pdfminer).

            # take most frequent font name and size
            self.font_size = Counter(int(c.height) for c in self.children).most_common()[0][0]
            self.font_name = Counter(c.fontname for c in self.children).most_common()[0][0]

    def render_style(self):
        sty = self.style
        if self.attributes.get('author', False):
            sty['background-color'] = 'rgba(255,0,0,0.25)'
        return ' '.join('%s: %s;' % x for x in sty.items())

    @property
    def tooltip(self):
        return '<pre>' + urllib.quote(pprint.pformat(self.attributes)) + '</pre>'


def gs(f, outdir):
    # where we'll put the images
    imgdir = os.path.abspath(outdir) + '/img'
    # have ghostscript render images of each page.
    #if not os.path.exists(imgdir):
    pdf2image(f, outputdir_fmt=imgdir, output_format=os.path.basename(f) + '-page-%d.png',
              moreopts='-dFirstPage=1 -dLastPage=1')


def convert(f):

    fp = open(f, 'rb')
    parser = PDFParser(fp)
    doc = PDFDocument()
    parser.set_document(doc)
    doc.set_parser(parser)

    rsrcmgr = PDFResourceManager()

    c = HTMLConverter(os.path.basename(f))

    laparams = LAParams(all_texts=True)

    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    for page in doc.get_pages():
        worked = False
        with ignore_error():
            interpreter.process_page(page)
            worked = True
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
        fontsize = Counter(x.font_size for x in items)
        freq = zip(fontsize.values(), fontsize.keys())
        freq.sort(reverse=True)
        rank = {k: rank + 1 for rank, (v, k) in enumerate(freq)}
        for x in items:
            x.attributes['fontsize-freq-rank'] = rank[x.font_size]

        # width frequency
        w = Counter(int(x.width) for x in items)
        freq = zip(w.values(), w.keys())
        freq.sort(reverse=True)
        rank = {k: rank + 1 for rank, (v, k) in enumerate(freq)}
        for x in items:
            x.attributes['width-rank'] = rank[int(x.width)]

        # fontsize rank
        fontsize = groupby2(items, lambda x: x.font_size)
        for rank, (_, vs) in enumerate(reversed(sorted(fontsize.items()))):
            for v in vs:
                v.attributes['fontsize-size-rank'] = rank + 1

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


def extract_title(filename):

    if not isinstance(filename, basestring):
        pdf = filename
        filename = pdf.filename
    else:
        try:
            pdf = convert(filename)
        except KeyboardInterrupt:
            raise
        except:
            return

    # check for skid-mark
    if os.path.exists(filename + '.d/notes.org'):
        from skid.add import Document
        d = Document(filename)
        meta = d.parse_notes()
        print meta.get(u'title', None)
        print meta.get(u'author', None)

    page = pdf.pages[0].items

    g = groupby2(page, key=lambda x: x.attributes['fontsize'])

    if not g:
        return

    title = ' '.join(x.attributes['text'].strip() for x in g[max(g)])

    print yellow % title.encode('utf8')

    g = groupby2(page, key=lambda x: x.attributes['fontname'])

    freq = [(len(v), k, v) for k,v in g.iteritems()]

    freq.sort()

    for count, key, items in freq:
        print
        print red % count, green % key
        for x in items[:10]:
            print yellow % x.attributes['text'].encode('utf8')
            print #'    ', [(k,v) for (k,v) in x.attributes.items() if k not in ('text', 'fontname', 'obj')]

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
            pdf = convert(filename)
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
