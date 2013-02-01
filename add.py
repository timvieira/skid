"""
Manage directory structure.
"""
import re, os, subprocess
from path import path

from skid.config import CACHE
from skid.common import mergedict, unicodify_dict, dictsubset

from arsenal.terminal import yellow, red, blue
from arsenal.web.download import download
from arsenal.text.utils import htmltotext, remove_ligatures, force_unicode, \
    whitespace_cleanup

from skid.pdfhacks import pdftotext, extract_title


# TODO: use wget instead, it's more robust and has more bells and
# whistles.. e.g. handling redirects, ftp, timeouts, and all sorts of silly
# things that happen when downloading a file.
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

        # TODO: explicitly tell cache_url where to put file (write-to location)

        # FIXME: check we haven't downloaded url already; check if the write-to
        # location file exists.

        return cache_url(src)

    elif src.exists():   # is this something on disk?

        dest = CACHE / src.basename()

        if dest.exists():
            # TODO: check if hash is the same. Suggest update methods or
            # renaming the file (possibly automatically, e.g. via hash).
            raise Exception('File %r already exists' % dest)

        src.copy2(dest)

        print 'copy:', src, '->', dest

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
#    - might want to handle most of this thru version control.
#    - check document already exists
#    - merges metadata
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

    d.write_hash()
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

    existingdata = d.note_content()

    newcontent = d.note_template(new)

    if dictsubset(new, old):
        d.meta('notes.org', newcontent, overwrite=True)

    elif newcontent.strip() != existingdata.strip():     # manual resolution
        merge_kdiff3(newcontent, d.d / 'notes.org')     # XXX: shouldn't hardcode path


def merge_kdiff3(newcontent, existing):
    "XXX: newcontent is a string; existing is a file."

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


# TODO: everything pertaining to Document should appear here probably including
# methods to: find most-similar documents, insert/delete/update index

# XXX: attributes fall into categories
# 1. backed by a file
# 2. extracted from notes
# 3. derived
class Document(object):

    def __init__(self, cached):
        self.cached = path(cached).expand().abspath()
        assert self.cached.exists()
        self.d = self.cached + '.d'

        if not self.d.exists():
            self.d.mkdir()
            (self.d / 'data').mkdir()

    def __repr__(self):
        return 'Document("%s")' % self.cached

    def edit_notes(self):
        subprocess.call([os.environ.get('EDITOR', 'nano'),
                         self.d / 'notes.org'])

    def meta(self, name, content, overwrite=False):
        t = self.d / name
        assert overwrite or not t.exists(), name + ' already exists!'
        with file(t, 'wb') as f:
            content = force_unicode(content)
            content = content.encode('utf8')
            f.write(content)
            f.write('\n')    # new line at end of file
        return content

    def write_hash(self):
        h = self.cached.read_hexhash('sha1')
        with file(self.d / 'data' / 'hash', 'wb') as f:
            f.write(h)
            f.write('\n')
        return h

    def extract_metadata(self):

        metadata = {'tags': '', 'title': '', 'notes': '', 'author': ''}
        if self.cached.endswith('.pdf'):
            metadata['title'] = extract_title(self.cached)

        else:
            # assume it's HTML
            x = re.findall('<title>(.*?)</title>', self.cached.text(), re.I)
            if x:
                metadata['title'] = x[0].strip()  # take the first title
            else:
                pass   # TODO: maybe take first line of the file?

        # user notes trump anything automatic
        parse = self.parse_notes()
        if parse:
            metadata = mergedict(metadata, parse)

        return metadata

    def text(self):
        return (self.d / 'data' / 'text').text().decode('utf8')

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

    def note_template(self, x):
        others = set(x) - set('title author source cached tags notes'.split())
        attrs = '\n'.join((':%s: %s' % (k, x[k])).strip() for k in others).strip()
        if attrs:
            attrs += '\n'
        newdata = TEMPLATE.format(attrs=attrs, **x)
        newdata = whitespace_cleanup(newdata)
        return force_unicode(newdata).encode('utf8').strip() + '\n'

    # TODO: do not like...
    def note_content(self):
        f = self.d / 'notes.org'
        if f.exists():
            return f.text()
#            return unicode(file(f).read().decode('latin1'))

    # TODO: use a lazy-loaded attribute?
    # TODO: better markup language?
    def parse_notes(self):
        "Extract metadata from notes.org."

        content = self.note_content()
        if not content:
            return

        # XXX: multiple value to same key.
        metadata = re.findall('^(?:\#\+?|:)([^:\s]+):[ ]*([^\n]*?)\s*$',
                              content, re.MULTILINE)

        x = {}
        for k, v in metadata:
            v = v.strip()
            if k in ('cached','source'):
                # remove org-mode's link markup
                v = re.sub('^\[\[(.*?)\]\]$', r'\1', v)
            x[k] = v

        [d] = re.findall('\n([^:#][\w\W]*$|$)', content)
        x['notes'] = d.strip()

        return unicodify_dict(x)


# TODO: date added. (is there a way to hide/collapse certain data in org-mode?
# should we just use file creation time?)
TEMPLATE = u"""\
#+title: {title}
:author: {author}
:source: [[{source}]]
:cached: [[{cached}]]
:tags: {tags}
{attrs}
{notes}
"""


# TODO: move to pdfhacks
# XXX: untested
# TODO: use me....
# TODO: use path.py
def to_pdf(filename):
    """ Hammer almost anything into a pdf. """

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
        return to_pdf('/tmp/tmp.ps')

    else:
        assert False, 'Unsupported file format.'
