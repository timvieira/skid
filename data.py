# find /home/timv/Desktop/ -name *.pdf -exec cp {} ~/.tags/cache/ \;
# find /home/timv/projects/read/ -name '*.pdf' -exec cp {} ~/.tags/cache/ \;

import os
from glob import glob
from iterextras import iterview
from BeautifulSoup import BeautifulSoup
from tags.pipeline import import_document, CACHE


def add_delicious(xml='delicious_timvieira.xml'):
    "Import delicious (xml) export data."
    with file(xml) as f:
        soup = BeautifulSoup(f)
        for post in iterview(soup.findAll('post')):
            print
            import_document(source = post['href'],
                            tags = post['tag'],
                            title = post['description'],
                            description = post['extended'])


def import_pdfs(pattern=CACHE + '/*.pdf'):
    "Import pdfs with file matching pattern."
    for source in iterview(glob(pattern)):
        if ' ' in source:
            print '[WARN] No spaces allowed in document source... renaming'
            newsource = source.replace(' ', '_')
            os.rename(source, newsource)
            source = newsource
        import_document(source, [])


def find_stuff_to_describe():
    for filename in glob(CACHE + '/*.pdf'):
        print filename
        assert os.path.exists(filename + '.d')

        description = filename + '.d/description'

        if file(description).read().strip():  # has description
            continue

        os.system('gnome-open ' + filename + ' 2>/dev/null &')

        os.system('/home/timv/projects/env/bin/visit ' + description)
        raw_input('hit enter for next')


def find_orphans():
    "Cleanup: find stray directories or files in cache."
    ds = set()
    xs = set()
    for x in glob(CACHE + '/*'):
        if x.endswith('.d'):
            ds.add(x[:-2])
        else:
            xs.add(x)
    for x in ds.symmetric_difference(xs):
        #assert x in ds
        #os.system('rm -r ' + x + '.d')
        print x


if __name__ == '__main__':
    from automain import automain
    automain()
