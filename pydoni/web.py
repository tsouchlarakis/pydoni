import pydoni


class Goodreads_Scrape(object):
    """
    Scrape all available information from page.

    :param url: goodreads URL to scrape
    :type url: str
    """

    def __init__(self):

        self.logger = pydoni.logger_setup(
            name=pydoni.what_is_my_name(classname=self.__class__.__name__, with_modname=True),
            level=pydoni.modloglev)

        self.url_base = 'https://www.goodreads.com'
        self.url_base_search = self.url_base + '/' + 'search?utf8=✓'

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

        :param search_string: string to search for, as if user were typing in the search box
        :type search_string: str
        """
        self.logger.logvars(locals())
        return '&q=%s&search_type=books' % search_string.replace(' ', '+')

    def get_top_result(self, search_string):
        """
        Execute Goodreads search and get the top result.

        :param search_string: string to search for, as if user were typing in the search box
        :type search_string: str
        :return: URL of top search result
        :rtype: str
        """
        from bs4 import BeautifulSoup
        self.logger.logvars(locals())

        query = self.build_query(search_string)
        url = self.url_base_search + query
        html = pydoni.web.simple_get(url)
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

        :param url: Goodreads book URL to scrape
        :type url: str
        :return: entire book data dictionary
        :rtype: dict
        """
        from bs4 import BeautifulSoup
        self.logger.logvars(locals())

        html = pydoni.web.simple_get(url)
        soup = BeautifulSoup(html, 'html.parser')
        items = [k for k, v in self.bookdict.items()]

        for item in items:
            self.bookdict[item] = self.__getbookattr__(soup, item)

        return self.bookdict

    def __getbookattr__(self, soup, attr):
        """
        Given `soup`, get book attribute by attribute name.

        :param soup: goodreads soup object for book page
        :type soup: bs4
        :param attr: attribute name to scrape
        :type attr: str
        :return: attribute value of book, None if attribute not found
        :rtype: any
        """
        import re

        assert attr in self.selector_map.keys()
        self.logger.logvars(locals())

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
                genres = [re.sub(r'\s+', ' ', x).strip() for x in genres]
                return ';'.join(genres)

        return None


def test_url(url, quiet=False):
    """
    Test if a url is available using the requests library.
    """
    import requests

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    try:
        requests.get(url)
        return True
    except Exception as e:
        if not quiet:
            logger.exception(e)
            logger.error(f'URL {url} not available')

        return False


def check_network_connection(abort=False):
    """
    Check if connected to internet

    :param abort: if True, quit program
    :type abort: bool
    :return: True if connected to internet, False if not
    :rtype: bool
    """
    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    is_network_connected = test_url('https://www.google.com', quiet=True)
    if abort and not is_network_connected:
        logger.error('No network connection!')
        import sys; sys.exit()

    return is_network_connected


def get_element_by_selector(url, selector, attr=None):
    """
    Extract HTML text by CSS selector.

    :param url: target URL to scrape
    :type url: str
    :param selector: CSS selector
    :type selector: str
    :param attr: name of attribute to extract
    :type attr: str
    :return: element value
    :rtype: str or list ir `attr` is specified
    """

    import requests
    from bs4 import BeautifulSoup

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')


    if attr:
        return [soup.select(selector)[i].attrs[attr] for i in range(len(soup.select(selector)))]

    elem = [soup.select(selector)[i].text for i in range(len(soup.select(selector)))]
    return elem


def get_element_by_xpath(url, xpath):
    """
    Extract HTML text by Xpath selector.

    :param url: target URL to scrape
    :type url: str
    :param xpath: xpath selector
    :type xpath: str
    :param attr: name of attribute to extract
    :type attr: str
    :return: element value
    :rtype: str or list ir `attr` is specified
    """
    import requests, html

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    page = requests.get(url)
    tree = html.fromstring(page.content)
    return tree.xpath(xpath)


def downloadfile(url, destfile=None, method='requests'):
    """
    Download file from the web to a local file.

    :param url: target URL to retrieve file from
    :type url: str
    :param destfile: target file to download to, must be specified if `method = 'requests'`.
                     If None, may use with `method = 'curl'`, and the -O flag will be passed
                     into curl to keep the original filename
    :type destfile: str
    :param method: method to use in downloading file, one of ['requests', 'curl']
    :type method: str
    """
    import shutil, requests

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

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

        pydoni.syscmd(cmd)


def download_audiobookslab(url, targetdir):
    """
    Download audiobooks off of audiobookslab.com webpage.

    :param url: audiobookslab.com webpage link to scrape
    :type url: str
    :param targetdir: path to directory to download files to. Will be created if it doesn't exist
    :type targetdir: str
    """
    import os
    from tqdm import tqdm

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    if not os.path.isdir(targetdir):
        os.mkdir(targetdir)
    os.chdir(targetdir)

    mp3_links = sorted(list(set(pydoni.web.get_element_by_selector(url, selector='audio'))))
    if len(mp3_links):
        with tqdm(total=len(mp3_links), unit='file') as pbar:
            for mp3_link in mp3_links:
                pbar.set_postfix(file=os.path.basename(mp3_link))
                pydoni.web.downloadfile(mp3_link, method='curl')
                pbar.update(1)
    else:
        error_msg = "No audiobooks to download at URL '%s'" % url
        logger.error(error_msg)
        raise Exception(error_msg)


def simple_get(url):
    """
    Attempts to get the content at `url` by making an HTTP GET request.
    If the content-type of response is some kind of HTML/XML, return the
    text content, otherwise return None.

    :param url: url to read
    :type url: str

    :return: {resp.content}
    """
    import contextlib
    import requests
    from requests.exceptions import RequestException

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    try:
        with contextlib.closing(requests.get(url, stream=True)) as resp:
            if pydoni.web.is_good_response(resp):
                return resp.content
            else:
                return None

    except RequestException as e:
        error_msg = 'Error during requests to {} : {}'.format(url, str(e))
        logger.error(error_msg)
        return None


def is_good_response(resp):
    """
    Returns True if the response seems to be HTML, False otherwise.

    :param resp: get response
    :type resp: resp

    :return: bool
    """

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    content_type = resp.headers['Content-Type'].lower()
    return (resp.status_code == 200
            and content_type is not None
            and content_type.find('html') > -1)


def scrape_reason_article(url):
    """
    Scrape article on Reason.com and write it as a text file.

    :param url: Reason article URL to scrape
    :type url: str
    :return: article text
    :rtype: str
    """

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    url = url.replace("\\?utm_medium", "?utm_medium")

    article = {}

    try:
        article['title'] = pydoni.web.get_element_by_selector(url, 'h1')
        logger.info('Scraped title successfully')
    except Exception as e:
        logger.exception("Failed to scrape title with element 'h1'")
        raise e

    try:
        article['body'] = pydoni.web.get_element_by_selector(url, '.entry-content p')
        logger.info('Scraped body successfully, length %s paragraphs' % str(len(article['body'])))
    except Exception as e:
        logger.exception("Failed to scrape body with element 'h1'")
        raise e

    if article['title'] == ['404 Error']:
        logger.critical("URL not found! Printed here: " + url)
        raise Exception('404 URL not found!')

    article = {k: '\n\n'.join(v) for k, v in article.items()}
    article_text = "{}\n\n{}".format(article['title'], article['body'])

    return article_text
