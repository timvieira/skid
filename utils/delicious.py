#!/usr/bin/env python

import sys
from urllib import urlopen
from getpass import getpass
from BeautifulSoup import BeautifulSoup

def delicious_export(username, filename='delicious_{username}.xml', password=None):
    """
    This is probably not the most secure way to do this because we are sending
    the password in plaintext over the wire.
    """

    filename = filename and filename.format(username=username)

    # API URL: https://user:passwd@api.del.icio.us/v1/posts/all
    url = "https://%s:%s@api.del.icio.us/v1/posts/all" % (username, password or getpass())
    content = urlopen(url).read()
    soup = BeautifulSoup(content)

    with file(filename, 'wb') as f:
        f.write(soup.prettify())

    return soup


if __name__ == '__main__':
    try:
        x = len(delicious_export(*sys.argv[1:]).findAll('post'))
        print 'retrieved', x, 'posts.'
    except TypeError:
        print sys.argv[0], 'username [outfile] [password]'
