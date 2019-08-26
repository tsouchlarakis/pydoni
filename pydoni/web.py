import requests
import shutil
import urllib
from bs4 import BeautifulSoup
from lxml import html

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
            quit()
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

def downloadfile(url, destfile):
    """
    Download file from the web to a local file.
    
    Arguments:
        url {str} -- target URL to retrieve file from
        destfile {str} -- target file to download to
    
    Returns:
        {str}
    """
    r = requests.get(url, stream=True)
    with open(destfile, 'wb') as f:
        r.raw.decode_content = True
        shutil.copyfileobj(r.raw, f)
