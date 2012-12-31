"""
Manage directory structure.

TODO:

  - pdftotext.txt should go in {cached}.d/data/

"""
import re, os, subprocess

from debug import ip
from terminal import yellow, red, blue, green
from fsutils import filetype
from web.download import download
from text.utils import htmltotext, remove_ligatures, force_unicode
from skid.config import CACHE

from os import environ
from path import path

from pdfhacks import pdftotext, extract_title

from skid.common import mergedict, unicodify_dict, dictsubset, parse_notes, \
    whitespace_cleanup


# TODO: use wget instead, it's more robust and has more bells and
# whistles.. e.g. handling redirects, timeouts, and all sorts of silly things
# that happen when downloading a file.
def cache_url(url):
    """
    Download url, write contents to file. Return filename of contents, None on
    failure to download.
    """
    # TODO: we should tell download where to store stuff explicitly... right now
    # we just both have the same convention.
    cached = download(url, tries=1, pause=0.1, timeout=60, usecache=True,
                      cachedir=CACHE)
    if not cached:
        raise Exception('Failed to download %s.' % url)

    return cached


def cache_document(src):
    "Cache a document, return filename of the cached file."

    # TODO: maybe support omitting 'http://', just guess that if its not a file
    # name it must be a url.

    # TODO:
    #  - make sure we don't overwrite files
    #  - cache to staging area first

    src = path(src)

    if src.startswith('http'):    # cache links
        return cache_url(src)

    elif src.exists():   # is this something on disk?

        dest = CACHE / src.basename()

        if dest.exists():
            raise Exception('File %r already exists' % dest)

        src.copy2(dest)

        print 'copy:', src, '->', dest

        # TODO: What if a .d directory exists near the file already?
        return dest

    assert False


# TODO: add file to Whoosh index.

# TODO:
#
# - "atomically" write directory to avoid issues with failures. Do this by
#   staging. This will help avoid clobbering existing stuff (notes, cached
#   document, etc)
#
# - If it's a pdf we should try to get a bibtex entry for it.
#
# - merge:
#
#    - might want to handle most of this thru version control.
#
#    - check document already exists
#
#    - merges metadata
#
#    - merge document contents (pick old or new version)
#
def document(source, tags='', title='', notes='', interactive=True):
    """
    Import document from ``source``. Procedure will download/cache the file,
    create a directory to store metadta.
    """

    assert ' ' not in source

    source = path(source)

    print blue % 'adding %s' % source

    # store the absolute path for local files.
    if source.exists():
        source = source.abspath()

    cached = cache_document(source)

    print cached

    d = Document(cached)

    d.hash_contents()
    d.extract_plaintext()

    update_existing(d, source, tags, title, notes)

    if interactive:
        d.edit_notes()



def update_existing(d, source, tags='', title='', notes=''):

    old = d.extract_metadata()

    # Adding a document from the cache is typically a "refresh", e.g. updating
    # the output of processing a file by pushing it through the pipeline. In
    # such an event we almost never want the source to change to the location of
    # the cached file. Thus, we handle the conflict automatically by using the
    # old source.
    if source.startswith(CACHE):
        source = old['source']

    new = {
        'notes': notes.strip(),
        'title': title,
        'source': source,
        'cached': d.cached,
    }

    new = mergedict(old, new)

    if tags:
        tags = tags.split() if isinstance(tags, basestring) else list(tags)
        # newtags will include all exisiting tags in the order the are listed in
        # document, concatenating new tags (ignoring duplicates; in order
        # listed).
        newtags = old['tags'].strip().split()
        existingtags = set(newtags)
        for t in tags:
            if t not in existingtags:
                newtags.append(t.strip())
        new['tags'] = ' '.join(newtags)

    new = unicodify_dict(new)
    old = unicodify_dict(old)

    existing = d.notes
    if existing.exists():
        existingdata = existing.text()
    else:
        existingdata = None

    newcontent = template(**new)

    if dictsubset(new, old):
        d.meta('notes.org', newcontent, overwrite=True)

    elif newcontent.strip() != existingdata.strip():     # manual resolution
        merge_kdiff3(newcontent, existing)



def merge_kdiff3(newcontent, existing):
    tmp = '/tmp/newmetadata.org'
    with file(tmp, 'wb') as f:
        f.write(newcontent)

    print red % 'Need to merge notes...'
    print yellow % '=================================='
    if 0 != os.system('kdiff3 --merge %s %s --output %s' % (existing, tmp, existing)):
        print red % 'merge aborted. keeping original, other temporarily saved to %s' % tmp

        # TODO: should probably delete any mess we might have made. This is
        # probably easier to do if we work in a staging area (we might not even
        # care to clean up after ourselves in that case).
        raise AssertionError('merging notes failed. aborting')
    else:
        print yellow % 'merge successful.'
        os.remove(existing + '.orig')  # remove kdiff's temporary file.


class Document(object):

    def __init__(self, cached):
        self.cached = path(cached).expand().abspath()
        assert self.cached.exists()
        self.d = self.cached + '.d'

        self.d.mkdir()
        (self.d / 'data').mkdir()

        self.filetype = filetype(self.cached)

        self.notes = self.d / 'notes.org'

    def __repr__(self):
        return 'Document("%s")' % self.cached

    def edit_notes(self):
        subprocess.call([environ.get('EDITOR', 'nano'), self.notes])

    def meta(self, name, content, overwrite=False):
        t = self.d / name
        assert overwrite or not t.exists(), name + ' already exists!'
        with file(t, 'wb') as f:
            content = force_unicode(content)
            content = content.encode('utf8')
            f.write(content)
            f.write('\n')    # new line at end of file
        return content

    def hash_contents(self):
        h = self.cached.read_hexhash('sha1')
        with file(self.d / 'data' / 'hash', 'wb') as f:
            f.write(h)
            f.write('\n')
        return h

    def extract_metadata(self):

        metadata = {'tags': '', 'title': '', 'notes': '', 'author': ''}
        if self.filetype.endswith('pdf'):
            metadata['title'] = extract_title(self.cached)

        else:
            # assume it's HTML
            x = re.findall('<title>(.*?)</title>', self.cached.text(), re.I)
            if x:
                metadata['title'] = x[0].strip()  # take the first title
            else:
                pass   # TODO: maybe take first line of the file?

        # user notes trump anything automatic
        if self.notes.exists():
            parse = parse_notes(self.notes.text())
            metadata = mergedict(metadata, parse)

        return metadata

    def extract_plaintext(self):
        "Extract plaintext from filename. Returns text, might cache."

        if self.cached.endswith('.pdf'):
            # extract text from pdfs
            text = pdftotext(self.cached, output=self.d / 'data' / 'pdftotext.txt',
                             verbose=True, usecached=True)

        else:
            text = self.cached.text()
            text = force_unicode(text)
            text = htmltotext(text)      # clean up html

        text = remove_ligatures(text)

        return self.meta('data/text', text, overwrite=True)


# XXX: untested
# TODO: use me....
# TODO: use path.py
def pdf_hammer(filename):

    s = filename.split('.')
    ext = s[-1]
    base = '.'.join(s[:-1])

    if ext in ('ppt', 'odf'):
        # convert 'ppt' and 'odf' to pdf
        assert 0 == os.system('libreoffice --headless --invisible --convert-to pdf %s' % filename)
        return base + '.pdf'

    elif ext in ('ps',):
        # convert postscript to pdf
        assert 0 == os.system('ps2pdf %s' % filename)
        return base + '.pdf'

    elif ext in ('ps.gz',):
        # TODO: convert ps.gz to pdf
        assert 0 == os.system('zcat %s > /tmp/tmp.ps' % filename)
        return pdf_hammer('/tmp/tmp.ps')



def template(**kwargs):
    others = set(kwargs) - set('title author source cached tags notes'.split())
    attrs = '\n'.join((':%s: %s' % (k, kwargs[k])).strip() for k in others).strip()
    if attrs:
        attrs += '\n'
    newdata = TEMPLATE.format(attrs=attrs, **kwargs)
    newdata = whitespace_cleanup(newdata)
    return force_unicode(newdata).encode('utf8').strip() + '\n'

TEMPLATE = u"""\
#+title: {title}
:author: {author}
:source: {source}
:cached: {cached}
:tags: {tags}
{attrs}
{notes}
"""
