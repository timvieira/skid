#!/usr/bin/env python
import bottle

import skid.index as ix

def get(x):
    return bottle.request.GET.get(x, '').strip()

from contextlib import contextmanager
from StringIO import StringIO
from arsenal.terminal.ansi2html import ansi2html
from arsenal.misc import ctx_redirect_io

@contextmanager
def redirect_io(convertansi=False):
    a = StringIO()
    with ctx_redirect_io() as b:
        yield a if convertansi else b
    if convertansi:
        a.write(ansi2html(b.getvalue(), template='<pre>%s</pre>'))

def route(*args, **kw):
    def wrap(f):
        @bottle.route(*args, **kw)
        def wrap2(*args2, **kw2):
            with redirect_io() as io:
                return f(*args2, **kw2) or io.getvalue()
        return wrap2
    return wrap


from skid.index import open_dir, MultifieldParser, DIRECTORY, NAME

ix = open_dir(DIRECTORY, NAME)
searcher = ix.searcher()
qp = MultifieldParser(fieldnames=['title', 'author', 'tags', 'notes', 'text'],
                      fieldboosts={'title': 5,
                                   'author': 5,
                                   'tags': 3,
                                   'notes': 2,
                                   'text': 1},
                      schema=ix.schema)

@route('/search')
def search():
    q = get('q') or '*'
    print 'query:', q, '<br/>'*2

    for hit in searcher.search(qp.parse(unicode(q.decode('utf8'))), limit=10):
        print '<div class="item">'
        print '<b>', hit['title'].strip(), '</b></br>'
        print '<a href="file://%s">cached</a>' % hit['cached']

        src = hit['source']
        if not src.startswith('http'):
            src = 'file://' + src
        print '<a href="%s">source</a>' % src
        print '<br/>'

        print ' '.join("""
<a href="Javascript:add_tag_to_query('%s')">%s</a>""" % (t, t) for t in hit['tags'].split())
        print '</div>'


@route('/')
def index():

    f = get('file')
    if f:
        return open(f).read()

    return """
<html>
<title>TODO</title>
<head>
<script type="text/javascript" src="/?file=prototype.js"></script>
<link rel="stylesheet" type="text/css" href="/?file=style.css"/>

<script type="text/javascript" language="javascript">

function add_tag_to_query(tag) {
    var q = $('query').value.trim() + " " + 'tags:' + tag; 
    search(q); 
    $('query').value = q;
}

function add_tooltip(elem) {
    if (elem.getAttribute('tooltip')) {
        elem.onclick = function(e) {
            var tooltip = elem.getElementsByClassName('popup');
            if (tooltip.length > 0) tooltip[0].toggle();
            else this.appendChild(new Element('div',{'class':'popup'}).update(unescape(this.getAttribute('tooltip'))));
        };
    }
}

// TODO: store current request and kill it if we get a new one
function ajax(url, params, obj) {
    var obj = $(obj || 'content');
    var req = new Ajax.Request(url, {
                    method: 'get',
                    parameters: params,
                    onSuccess: function(transport) { obj.update(unescape(transport.responseText)); },
                    onFailure: function() { obj.update('Something went wrong...'); }
    });
}

// TODO: check if changed before making sending query
function search(q) { ajax('/search?', {q:q}); }
function onload() {
   //search();
}

</script>
</head>
<body onload="onload()">

<div id="debug"></div>

<div id="middle">

<form method="get" action="Javascript:search($('query').value)">
    <textarea cols="70" rows="2" id="query"></textarea>
    <input type="submit" value="Find" />
</form>

<div id="content"></div>

</div>

<script type="text/javascript">
//    $('query').observe('keyup', function (e) { search(Event.element(e).value); } );
</script>

</body></html>"""


def run():
    from arsenal.fsutils import cd
    import os
    import webbrowser; webbrowser.open('http://localhost:8080')
    bottle.debug(True)

    with cd(os.path.dirname(__file__)):
        bottle.run(reloader=False)

if __name__ == '__main__':
    run()
