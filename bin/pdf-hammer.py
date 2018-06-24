#!/usr/bin/env python
from os import system
from path import Path as path


# TODO: check if text extraction is any good
# TODO: check if required executables exist.
def hammer(filename):
    """ Hammer almost anything into a pdf. """

    f = path(filename)

    assert f.exists(), 'Input file `%s` does not exist.' % f

    # desired output filename
    out = f.dirname() / f.namebase + '.pdf'

    if f.ext in ['.ppt', '.odf']:
        # convert 'ppt' and 'odf' to pdf
        assert 0 == system('libreoffice --headless --invisible' \
                           ' --convert-to pdf %s --outdir %s' % (f, f.dirname()))
        return out

    elif f.ext in ['.ps', '.eps']:
        # convert postscript to pdf
        assert 0 == system('ps2pdf %s %s' % (filename, out))
        return out

    elif f.ext in ['.ps.gz']:
        # TODO: convert ps.gz to pdf
        assert 0 == system('zcat %s > /tmp/tmp.ps' % filename)
        return hammer('/tmp/tmp.ps')

    elif f.ext in ['.djvu']:
        # convert djvu to pdf
        #ddjvu -format=pdf -quality=85 -verbose "$1" "$1.pdf"
        assert False, 'djvu not conversion not yet supported.'

    else:
        assert False, 'Unsupported file format.'


def main():
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('filename')
    args = parser.parse_args()
    out = hammer(args.filename)
    assert path(out).exists(), 'Something went wrong.' \
        'File `%s` does not exist.' % out
    print 'wrote', out


if __name__ == '__main__':
    main()
