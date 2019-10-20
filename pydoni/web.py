import requests
import shutil
import urllib
from os import chdir, mkdir
from os.path import isdir, basename
from bs4 import BeautifulSoup
from lxml import html
from tqdm import tqdm


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