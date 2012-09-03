"""
Import data from a few different sources.
"""

# find /home/timv/Desktop/ -name *.pdf -exec cp {} ~/.skid/marks/ \;
# find /home/timv/projects/read/ -name '*.pdf' -exec cp {} ~/.skid/marks/ \;

import os
from glob import glob
from iterextras import iterview
from BeautifulSoup import BeautifulSoup
from skid.pipeline import add, CACHE


def delicious(xml):
    "Import delicious (xml) export data."
    with file(xml) as f:
        soup = BeautifulSoup(f)
        for post in iterview(soup.findAll('post')):
            print
            add(source = post['href'],
                tags = post['tag'],
                title = post['description'],
                description = post['extended'],
                interactive = False)


def pdfs(pattern=CACHE + '/*.pdf'):
    "Import pdfs with file matching pattern."
    for source in iterview(glob(pattern)):
        if ' ' in source:
            print '[WARN] No spaces allowed in document source... renaming'
            newsource = source.replace(' ', '_')
            os.rename(source, newsource)
            source = newsource
        add(source = source,
            tags = [],
            interactive = False)
