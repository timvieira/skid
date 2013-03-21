import urllib, httplib
from BeautifulSoup import BeautifulSoup

from arsenal.terminal import red, yellow, green, blue
from arsenal.text import htmltotext


def search(terms, limit=10, SEARCH_HOST = "scholar.google.com", SEARCH_BASE_URL = "/scholar"):

    params = urllib.urlencode({'q': "+".join(terms), 'num': limit})
    headers = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'}

    url = SEARCH_BASE_URL + "?" + params
    conn = httplib.HTTPConnection(SEARCH_HOST)
    conn.request("GET", url, headers=headers)

    resp = conn.getresponse()

    print resp.status

    if resp.status == 200:
        html = resp.read()
        html = html.decode('ascii', 'ignore')

        # Screen-scrape the result to obtain the publication information
        soup = BeautifulSoup(html)

        #with file('results.html', 'wb') as f:
        #    f.write(soup.prettify())

        for record in soup.findAll('div', {'class': 'gs_ri'}):

            #print record.prettify()

            link = record.first('a')

            title = htmltotext(' '.join(map(unicode, link.contents))).strip()
            href = link['href']

            if href.startswith('http'):

                yield {
                    'title': title,
                    'href': href,
                    'raw': record.prettify(),
                }


if __name__ == '__main__':
    import sys
    if not sys.argv[1:]:
        print 'give me something to search for...'
        sys.exit(1)

    for pub in search(sys.argv[1:], 10):
        print red % '======================================================================'
        print yellow % pub['title']
        print green % pub['href']

