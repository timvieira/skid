import os

# convert {ppt, odf} to pdf
#libreoffice --headless --invisible --convert-to pdf

# convert djvu to pdf
#ddjvu -format=pdf -quality=85 -verbose "$1" "$1.pdf"

# covert ps to pdf
#ps2pdf

# TODO: check if text extraction is any good


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
