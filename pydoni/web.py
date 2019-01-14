def CheckNetworkConnection(stopifnot=False):  # Check if connected to internet
    import urllib.request
    try:
        urllib.request.urlopen('https://www.google.com')
        return True
    except:
        if stopifnot:
            exit()
        else:
            return False

def getElementBySelector(url, selector, attr=None):  # Defaults to extracting HTML text
    import requests
    from bs4 import BeautifulSoup
    try:
        page = requests.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')
        if attr:
            return [soup.select(selector)[i].attrs[attr] for i in range(len(soup.select(selector)))]
        elem = [soup.select(selector)[i].text for i in range(len(soup.select(selector)))]
        return elem
    except Exception as e:
        from pydoni.vb import echo
        echo("Unable to parse {} for element {}".format(
            clickfmt(url, fmt='url'), clickfmt(selector, fmt='red')), str(e),
            fn_name='GetElementBySelector', error=True)

def downloadfile(url, destfile):
    import requests, shutil
    r = requests.get(url, stream=True)
    with open(destfile, 'wb') as f:
        r.raw.decode_content = True
        shutil.copyfileobj(r.raw, f)