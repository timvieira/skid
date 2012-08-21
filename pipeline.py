import os
from debug import ip
from terminal import yellow, red, blue, green
from fsutils import mkdir, filetype
from pdfutils.conversion import pdftotext
from web.download import download
from text.utils import htmltotext, remove_ligatures, force_unicode


CACHE = '/home/timv/.tags/cache'


def plaintext(filename):
    "Extract plaintext from filename. Returns text, might cache."

    # TODO: doesn't work on my urls e.g. "http://google.com" b/c there's no ext.
    ext = os.path.splitext(filename)[1][1:]  # remove the dot

    if ext == 'pdf':
        # extract text from pdfs
        text = pdftotext(filename, verbose=True, usecached=True)

    else:
        with file(filename, 'r') as f:
            text = f.read()
        text = force_unicode(text)

        # clean up html
        text = htmltotext(text)

    text = remove_ligatures(text)

    return text


def cache_url(url):
    """
    Download url, write contents to file. Return filename of contents, None on
    failure to download.
    """

    try:

        # TODO: we should be telling download where to store stuff
        # explicitly... right now we just both have the same convention.
        cached = download(url, tries=3, usecache=True, cachedir=CACHE)
        if not cached:
            print 'Failed to download %s.' % url
            return

    except KeyboardInterrupt:
        return

    return cached


def cache_document(source):
    "Cache a document, return filename of the cached file."

    if source.startswith('http'):    # cache links
        return cache_url(source)

    elif os.path.exists(source):   # is this something on disk?

        # TODO: make symlink and .d directory inside cache. What if the .d
        # directory exists near the file already?
        return source

    else:
        assert False


def import_document(source, tags, title='', description=''):
    """
    Import document from ``source``. Procedure will download/cache the file,
    create a directory to store metadta.
    """

    print blue % 'adding %s' % source

    assert ' ' not in source

    if isinstance(tags, basestring):
        tags = tags.split()

    # classify
    if os.path.exists(source):         # is this something on disk?
        tags.append('$local')
    elif source.startswith('http'):    # cache links
        tags.append('$url')

    cached = cache_document(source)

    print 'filetype:', filetype(cached)
    tags.append('$filetype:' + filetype(cached))

    print cached

    if cached:
        tags.append('$cached')
    else:
        tags.append('$failed-to-cache')

    print 'dir:', cached + '.d'
    mkdir(cached + '.d')

    def meta(name, content):
        with file(cached + '.d/' + name, 'wb') as f:
            if not isinstance(content, basestring):
                content = '\n'.join(content)
            content = force_unicode(content)
            content = content.encode('utf8')
            f.write(content)
            f.write('\n')    # new line at end of file

    if cached:
        text = plaintext(cached)
        meta('text', text)
        meta('tags', tags)
        meta('title', title)
        meta('description', description)
        meta('source', source)


if __name__ == '__main__':
    from automain import automain
    automain()
