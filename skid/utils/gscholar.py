#!/usr/bin/env python

# gscholar - Get bibtex entries from Goolge Scholar
# Copyright (C) 2011  Bastian Venthur <venthur at debian org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


"""Library to query Google Scholar.

Call the method query with a string which contains the full search string.
Query will return a list of bibtex items.



Requirements
============

 * Python
 * pdftotext (command line tool)


Using gscholar as a command line tool
=====================================

Put gscholar.py in your path (e.g. by putting it in your ~/bin/), to call it
from any directory.


Making a simple lookup:
-----------------------

    gscholar.py "some author or title"

will return the first resut from Google Scholar matching this query.


Getting more results:
---------------------

    gscholar.py --all "some author or title"

Same as above but returns up to 10 bibtex items. (Use with caution Google will
assume you're a bot an ban you're IP temporarily)


Querying using a pdf:
---------------------

    gscolar.py /path/to/pdf

Will read the pdf to generate a Google Scholar query. It uses this query to
show the first bibtex result as above.


Renaming a pdf:
---------------

    gscholar.py --rename /path/to/pdf

Will do the same as above but asks you if it should rename the file according
to the bibtex result. You have to answer with "y", default answer is no.


Getting help:
-------------

    gscholar.py --help



Using gscholar as a python library
==================================

Copy the package somewhere Python can find it.

    import gscholar

    gscholar.query("some author or title")

will return a list of bibtex items.


"""


import urllib2
import re
import hashlib
import random
import sys
import os
import subprocess
import optparse
import logging
from htmlentitydefs import name2codepoint



# fake google id (looks like it is a 16 elements hex)
google_id = hashlib.md5(str(random.random())).hexdigest()[:16]

GOOGLE_SCHOLAR_URL = "http://scholar.google.com"
# the cookie looks normally like:
#        'Cookie' : 'GSP=ID=%s:CF=4' % google_id }
# where CF is the format (e.g. bibtex). since we don't know the format yet, we
# have to append it later
HEADERS = {'User-Agent' : 'Mozilla/5.0',
           'Cookie' : 'GSP=ID=%s' % google_id }


BIBTEX = 4


def query(searchstr, allresults=False):
    """Return a list of bibtex items."""
    logging.debug("Query: %s" % searchstr)
    searchstr = '/scholar?q='+urllib2.quote(searchstr)
    url = GOOGLE_SCHOLAR_URL + searchstr

    print url

    header = HEADERS
    header['Cookie'] = header['Cookie'] + ":CF=%d" % BIBTEX
    request = urllib2.Request(url, headers=header)
    response = urllib2.urlopen(request)
    html = response.read()
    html.decode('ascii', 'ignore')
    # grab the links
    tmp = get_links(html)

    # follow the bibtex links to get the bibtex entries
    result = list()
    if not allresults and len(tmp) != 0:
        tmp = [tmp[0]]
    for link in tmp:
        url = GOOGLE_SCHOLAR_URL+link
        request = urllib2.Request(url, headers=header)
        response = urllib2.urlopen(request)
        bib = response.read()

# TODO: this should probably be a debugging option.
#        print
#        print
#        print bib
        result.append(bib)
    return result


def get_links(html):
    """Return a list of reference links from the html."""

#    results = [(a,b) for a,b in re.findall('<a.*?href="(.*?)".*?>(.*?)</a>', html) if '[PDF]' in b]
#    from arsenal.debug import ip; ip()

    reflist = re.findall(r'<a href="(/scholar\.bib\?[^>]*)">', html)
    
    # escape html enteties
    escape = lambda m: unichr(name2codepoint[m.group(1)])
    return [re.sub('&(%s);' % '|'.join(name2codepoint), escape, s) for s in reflist]


def convert_pdf_to_txt(pdf):
    """Convert a pdf file to txet and return the text.

    This method requires pdftotext to be installed.
    """
    stdout = subprocess.Popen(["pdftotext", "-q", pdf, "-"], stdout=subprocess.PIPE).communicate()[0]
    return stdout


def pdflookup(pdf, allresults=False):
    """Look a pdf up on google scholar and return bibtex items."""
    txt = convert_pdf_to_txt(pdf)
    # remove all non alphanumeric characters
    words = re.findall('\w\w\w\w+', txt)[:20]  # query first 20 words longer than 4 characters in document
    gsquery = " ".join(words)
    bibtexlist = query(gsquery, allresults)
    return bibtexlist


def _get_bib_element(bibitem, element):
    """Return element from bibitem or None."""
    lst = [i.strip() for i in bibitem.split("\n")]
    for i in lst:
        if i.startswith(element):
            value = i.split("=", 1)[-1]
            value = value.strip()
            while value.endswith(','):
                value = value[:-1]
            while value.startswith('{') or value.startswith('"'):
                value = value[1:-1]
            return value
    return None


def rename_file(pdf, bibitem):
    """Attempt to rename pdf according to bibitem."""

    year = _get_bib_element(bibitem, "year")
    author = _get_bib_element(bibitem, "author")
    if author:
        author = author.split(",")[0]
    title = _get_bib_element(bibitem, "title")
    l = []
    for i in year, author, title:
        if i:
            l.append(i)
#    filename =  " - ".join(l) + ".pdf"

    filename = (author + year[-2:] + title.split()[0] + '.pdf').lower()

    newfile = pdf.replace(os.path.basename(pdf), filename)
    print
    print "Will rename:"
    print
    print "  %s" % pdf
    print
    print "to"
    print
    print "  %s" % newfile
    print
    print "Proceed? [y/N]"
    answer = raw_input()
    if answer == 'y':
        print "Renaming %s to %s" % (pdf, newfile)
        os.rename(pdf, newfile)
    else:
        print "Aborting."


import argparse
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--all', action='store_true', default=False,
                        help='show all bibtex results')
    parser.add_argument('--debug', action='store_true', default=False,
                        help='show debugging output')
    parser.add_argument('--rename', action='store_true', default=False,
                        help='rename file (asks before doing it)')
    parser.add_argument('query', nargs='+',
                        help='Search terms or pdf.')

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    if not args.query:
        parser.error("No argument given, nothing to do.")
        sys.exit(1)

    q = ' '.join(args.query)
    pdfmode = False

    if os.path.exists(q):
        logging.debug("File exist, assuming you want me to lookup the pdf: %s." % q)
        pdfmode = True
        biblist = pdflookup(q, args.all)
    else:
        logging.debug("Assuming you want me to lookup the query: %s." % q)
        biblist = query(q, args.all)

    if not biblist:
        print "No results found, try again with a different query!"
        sys.exit(1)

    if args.all:
        logging.debug("All results:")
        for i in biblist:
            print i
    else:
        logging.debug("First result:")
        print biblist[0]

    if args.rename:
        if not pdfmode:
            print "You asked me to rename the pdf but didn't tell me which file to rename, aborting."
            sys.exit(1)
        else:
            rename_file(q, biblist[0])


if __name__ == "__main__":
    main()
