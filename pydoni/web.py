import re
import requests
import shutil
import urllib
from bs4 import BeautifulSoup
from contextlib import closing
from lxml import html
from os import chdir
from os import mkdir
from os.path import  basename
from os.path import isdir
from os.path import join
from requests import get
from requests.exceptions import RequestException
from tqdm import tqdm


class Goodreads_Scrape(object):
    """
    Scrape all available information from page.

    Arguments:
        url {str} -- goodreads URL to scrape
    """

    def __init__(self):
        self.url_base = 'https://www.goodreads.com'
        self.url_base_search = join(self.url_base, 'search?utf8=✓')
        self.bookdict = {
            'title': None,
            'author': None,
            'year': None,
            'pages': None,
            'genre': None
        }
        self.selector_map = {
            'title': '#bookTitle',
            'author': '.authorName span',
            'year': '.row .greyText',
            'pages': '.row:nth-child(1)',
            'genre': '.elementList'
        }

    def build_query(self, search_string):
        """
        Build goodreads search query to be appended to base URL.

        Arguments:
            search_string {str} -- string to search for, as if user were typing in the search box
        """
        return '&q=%s&search_type=books' % search_string.replace(' ', '+')

    def get_top_result(self, search_string):
        """
        Execute Goodreads search and get the top result.

        Arguments:
            search_string {str} -- string to search for, as if user were typing in the search box 

        Returns:
            {str} -- URL of top search result
        """
        query = self.build_query(search_string)
        url = self.url_base_search + query
        html = simple_get(url)
        soup = BeautifulSoup(html, 'html.parser')
        res = soup.findAll('a', {'class': 'bookTitle'})
        hrefs = []
        
        for x in res:
            if 'href' in x.attrs.keys():
                hrefs.append(x['href'])
        
        return self.url_base + hrefs[0]

    def scrape_book_page(self, url):
        """
        Scrape webpage HTML and assign all values to `self.bookdata`.

        Arguments:
            url {str} -- Goodreads book URL to scrape
        """
        html = simple_get(url)
        soup = BeautifulSoup(html, 'html.parser')
        items = [k for k, v in self.bookdict.items()]
        
        for item in items:
            self.bookdict[item] = self.__getbookattr__(soup, item)
        
        return self.bookdict

    def __getbookattr__(self, soup, attr):
        """
        Given `soup`, get book attribute by attribute name.

        Arguments:
            soup {bs4} -- goodreads soup object for book page
            attr {str} -- attribute name to scrape
        """

        assert attr in self.selector_map.keys()
        selector = self.selector_map[attr]
        match = soup.select(selector)

        if len(match):
            if attr == 'title':
                booktitles = [item.text for item in match]
                title = booktitles[0]
                title = re.sub(r'\s+', ' ', title)
                title = title.replace(':', '_').replace('’', "'")
                return title
            
            elif attr == 'author':
                author = [item.text for item in match][0]
                author = re.sub(r'\s+', ' ', author)
                return author

            elif attr == 'year':
                years = []
                for item in match:
                    try:
                        text = item.text
                        text = re.sub(r'\s+', ' ', text).strip()
                        m = re.search(r'published \d{4}', text).group(0)
                        years.append(m.replace('published', '').strip())
                    except:
                        pass

                if len(years):
                    return years[0]

            elif attr == 'pages':
                pages = [item.text for item in match]
                pages = pages[0]
                pages = re.search(r'\d+ pages', pages).group(0)
                return pages.replace('pages', '').strip()

            elif attr == 'genre':
                genres = [item.text.strip() for item in match]
                genres = [re.sub(r'(\d),(\d)', r'\1\2', x) for x in genres]
                genres = [re.sub(r'\d+ users', '', x) for x in genres]
                genres = [re.sub('\s+', ' ', x).strip() for x in genres]
                return ';'.join(genres)

        return None


def check_network_connection(abort=False):
    """
    Check if connected to internet
    
    Arguments:
        abort {bool} -- if True, quit program
    
    Returns:
        {bool}
    """
    try:
        urllib.request.urlopen('https://www.google.com')
        return True
    except:
        if abort:
            from pydoni.vb import echo
            echo('No internet connection!', abort=True)
        else:
            return False


def get_element_by_selector(url, selector, attr=None):
    """
    Extract HTML text by CSS selector.
    
    Arguments:
        url {str} -- target URL to scrape
        selector {str} -- CSS selector
        attr {str} -- name of attribute to extract
    
    Returns:
        {str}
    """
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')
    if attr:
        return [soup.select(selector)[i].attrs[attr] for i in range(len(soup.select(selector)))]
    elem = [soup.select(selector)[i].text for i in range(len(soup.select(selector)))]
    return elem
    

def get_element_by_xpath(url, xpath):
    """
    Extract HTML text by Xpath selector.
    
    Arguments:
        url {str} -- target URL to scrape
        selector {str} -- CSS selector
        attr {str} -- name of attribute to extract
    
    Returns:
        {str}
    """
    page = requests.get(url)
    tree = html.fromstring(page.content)
    return tree.xpath(xpath)


def downloadfile(url, destfile=None, method='requests'):
    """
    Download file from the web to a local file.
    
    Arguments:
        url {str} -- target URL to retrieve file from

    Keyword Arguments:
        destfile {str} -- target file to download to, must be specified if `method = 'requests'`. If None, may use with `method = 'curl'`, and the -O flag will be passed into curl to keep the original filename
        method {str} -- method to use in downloading file, one of ['requests', 'curl'] (default: {'requests'})
    
    Returns:
        {str}
    """

    assert method in ['requests', 'curl']

    if method == 'requests':
        assert isinstance(destfile, str)

        r = requests.get(url, stream=True)
        with open(destfile, 'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)

    elif method == 'curl':
        if isinstance(destfile, str):
            cmd = 'curl -o "{}" "{}"'.format(destfile, url)
        else:
            cmd = 'curl -O "{}"'.format(url)
        syscmd(cmd)


def download_audiobookslab(url, targetdir):
    """
    Download audiobooks off of audiobookslab.com webpage.

    Arguments:
        url {str} -- audiobookslab.com webpage link to scrape
        targetdir {str} -- path to directory to download files to. Will be created if it doesn't exist

    Returns:
        nothing
    """

    if not isdir(targetdir):
        mkdir(targetdir)
    chdir(targetdir)

    mp3_links = sorted(list(set(get_element_by_selector(url, selector='audio'))))
    if len(mp3_links):
        with tqdm(total=len(mp3_links), unit='file') as pbar:
            for mp3_link in mp3_links:
                pbar.set_postfix(file=basename(mp3_link))
                downloadfile(mp3_link, method='curl')
                pbar.update(1)
    else:
        echo("No audiobooks to download at URL '%s'" % url, abort=True)


def simple_get(url):
    """
    Attempts to get the content at `url` by making an HTTP GET request.
    If the content-type of response is some kind of HTML/XML, return the
    text content, otherwise return None.

    Arguments:
        url {str} -- url to read

    Returns:
        {resp.content}
    """
    try:
        with closing(get(url, stream=True)) as resp:
            if is_good_response(resp):
                return resp.content
            else:
                return None
    except RequestException as e:
        echo('Error during requests to {0} : {1}'.format(url, str(e)))
        return None


def is_good_response(resp):
    """
    Returns True if the response seems to be HTML, False otherwise.

    Arguments:
        resp {resp.content} -- get response

    Returns:
        {bool}
    """
    content_type = resp.headers['Content-Type'].lower()
    return (resp.status_code == 200 
            and content_type is not None 
            and content_type.find('html') > -1)


from pydoni.sh import syscmd
from pydoni.vb import echo