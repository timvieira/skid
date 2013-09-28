"""
Import data from a few different sources.
"""

import os
from glob import glob
from BeautifulSoup import BeautifulSoup
from arsenal.iterextras import iterview
from skid import add

def delicious(xml):
    "Import links from delicious xml export. E.g. the output of delicious_import.py"
    with file(xml) as f:
        soup = BeautifulSoup(f)
        for post in iterview(soup.findAll('post')):
            print
            add.document(source = post['href'],
                         tags = post['tag'],
                         title = post['description'],
                         notes = post['extended'],
                         interactive = False)

def pdfs(pattern):
    "Import pdfs with file matching pattern."
    for source in iterview(glob(pattern)):
        if ' ' in source:
            print '[WARN] No spaces allowed in document source... renaming'
            newsource = source.replace(' ', '_')
            os.rename(source, newsource)
            source = newsource
        add.document(source = source,
                     tags = [],
                     interactive = False)
