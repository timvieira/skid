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

import os, sys, pprint, random, urllib
from arsenal.iterextras import groupby2
from arsenal.text.utils import remove_ligatures
from arsenal.debug import ip
from arsenal.terminal import red, green, blue, yellow

from skid.pdfhacks.conversion import pdf2image

# pdfminer
from pdfminer.layout import LAParams, LTAnon, LTPage, LTLine, LTRect, \
    LTTextLine, LTTextBox, LTFigure
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

run_feature_extraction = 0

if run_feature_extraction:
    from skid.pdfhacks import features


def random_color():
    return tuple(random.randint(0,255) for i in xrange(3))

def add_style(item, style):
    if not hasattr(item, 'style'):
        item.style = ''
    item.style += style


def feature_extraction(item):
    item.attributes = {}

    position = {'x0': item.x0, 'y0': item.y0, 'x1': item.x1, 'y1': item.y1}
    item.attributes.update(position)

    if not isinstance(item, LTTextLine):
        return

    #text = pprint.pformat(item.get_text().strip())[2:-1]
    text = item.get_text().strip()
#    text = remove_html_escapes(text)
    text = remove_ligatures(text)

    item.attributes['text'] = text

    children = [c for c in item if hasattr(c, 'fontname')]
    if children:
        # this isn't really font size, its height of the character bbox, which
        # might be better because it invariant to font type.
        item.attributes['font-size'] = int(min(c.height for c in children))
        item.attributes['font-name'] = children[0].fontname

    if not run_feature_extraction:
        return

    layout = {
        'ends-with-hyphen': text.endswith('-'),
    }

    textual = {
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
        self.height = item.height
        self.width = item.width
        self.yoffset = item.yoffset
        self.attributes = item.attributes

        self.x0 = item.x0
        self.x1 = item.x1
        self.y0 = item.y0
        #self.y1 = item.y1 is often unreliable
        self.y1 = item.y0 + item.height

        assert self.x0 <= self.x1 and self.y0 <= self.y1
        assert abs(self.x1 - (self.x0 + self.width)) <= 1   # allow one pixel of error..
        assert abs(self.y1 - (self.y0 + self.height)) <= 1  # "

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
        interpreter.process_page(page)
        layout = device.get_result()
        c.current_page = page
        c.render(layout)
        break  # stop after first page.

    return c


class HTMLConverter(object):

    def __init__(self, filename):
        self.filename = filename
        self.yoffset = 0
        self.pages = []
        self.text_lines = []
        self.items = []
        self.current_page = None

    def draw_item(self, c, item):

        # bounding box canonicalization
        item.x0 = int(min(item.x0, item.x1))
        item.x1 = int(max(item.x0, item.x1))
        item.y0 = int(min(item.y0, item.y1))
        item.y1 = int(max(item.y0, item.y1))
        item.width = int(item.width)
        item.height = int(item.height)

        add_style(item, 'border: %s;' % c)

        feature_extraction(item)

        # format the tooltip
        if isinstance(item, LTTextLine):
            item.tooltip = '<pre>' + urllib.quote(pprint.pformat(item.attributes)) + '</pre>'
        else:
            item.tooltip = ''

        item.yoffset = item.y0 + item.page.yoffset
        item.page.boxes.append(item)

        if isinstance(item, LTTextLine):
            self.items[-1].append(MyItem(item))

    def render(self, item):

        if isinstance(item, LTAnon):  # appears to be the space character
            return

        if isinstance(item, LTPage):
            item.yoffset = self.yoffset
            self.yoffset += item.height

            self.current_page = item

            if not hasattr(self.current_page, 'imgfile'):
                self.current_page.imgfile = '%s-page-%s.png' % (self.filename, len(self.pages) + 1)

            item.boxes = []
            #item.img_src = "{self.imgdir}/{page.id}.png".format(self=self, page=item)
            self.pages.append(item)
            self.items.append([])
            item.items = []
            for child in item:
                self.render(child)

            return

        # give item a reference to the page it's on, and the other way around as well.
        item.page = self.pages[-1]
        self.pages[-1].items.append(item)

        # apply coordinate transformation; item is currently "upside down"
        item.y0 = item.page.height - item.y0
        item.y1 = item.page.height - item.y1
        item.height = item.y0 - item.y1

        if isinstance(item, LTLine):
            pass
        elif isinstance(item, LTRect):
            pass

        elif isinstance(item, LTTextLine):
            self.draw_item('thin solid orange', item)
            self.text_lines.append(item)
            for child in item:
                self.render(child)

        # these are higher-level things like paragraphs and headings, but very noisy.
        elif isinstance(item, LTTextBox):
            self.draw_item('2px solid red', item)
            color = random_color()
            for child in item:
                self.render(child)
                add_style(child, 'background-color: rgba(%s,%s,%s,0.5);' % color)

        elif isinstance(item, LTFigure):
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

    % for item in page.boxes:
        <div style="position:absolute;
                    ${item.style}
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


    for page in pdf.items:

        #for x in page: x.attributes['obj'] = x
        """
        from pandas import DataFrame
        df = DataFrame([x.attributes for x in page])

        if 'font-size' not in df.columns or 'font-name' not in df.columns:
            continue

        df1 = df.set_index(['font-size', 'font-name']).sort(ascending=False)

#        for k,v in df.groupby(['font-size', 'font-name'], sort=True):
#            print '-----'
#            print k,v

#        print '______________________________'
#        print df1.to_string()
        """
        g = groupby2(page, key=lambda x: x.attributes['font-size'])

        if not g:
            continue  # try the next page...

        title = ' '.join(x.attributes['text'].strip() for x in g[max(g)])

        print yellow % title

        g = groupby2(page, key=lambda x: x.attributes['font-name'])

        freq = [(len(v), k, v) for k,v in g.iteritems()]

        freq.sort()

        for count, key, items in freq:
            print
            print red % count, green % key
            for x in items[:10]:
                print yellow % x.attributes['text'] #, [(k,v) for (k,v) in x.attributes.items() if k not in ('text', 'font-name', 'obj')]

#        from debug import ip; ip()

#        print red % 'EXITING'
#        exit(1)

        return title


def main(filenames):

    outdir = 'tmp'
    outfile = outdir + '/output.html'

    pages = []
    for filename in filenames:

        print
        print green % filename
        try:
            pdf = convert(filename)
        except KeyboardInterrupt:
            continue
        except:
            pdf = None
            print yellow % 'ERROR'
        else:

            print yellow % extract_title(pdf)

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
