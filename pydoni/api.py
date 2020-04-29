import pydoni


class Goodreads(object):
    """
    Extract Goodreads data for a title.

    :param api_key: Goodreads API key string
    :type api_key: str

    Notes:
        self.api_key = 'XRdjRL9pCqTj4pUMyG1jyQ'
        self.api_secret = '7zqBFszYrh3InYCMLZ2gyZXC1VPad2BELRWLXEU0bI'
    """

    def __init__(self, api_key):

        import goodreads_api_client as gr
        
        self.logger = pydoni.logger_setup(
            name=pydoni.what_is_my_name(classname=self.__class__.__name__, with_modname=True),
            level=pydoni.modloglev)
        
        if not api_key > '':
            errmsg = 'Must enter a valid API key!'
            self.logger.critical(errmsg, exc_info=True)
            raise Exception(errmsg)

        self.client = gr.Client(developer_key=api_key)
        self.book = None
        self.bookdata = {}
        self.bookdf = None

    def search_id(self, id):
        """
        Search the Goodreads API for a book by its ID.

        :param id: Goodreads ID string
        :type id: str
        :return: book name
        :rtype: str
        """
        self.logger.info("Searching for ID: '%s'" % str(id))
        self.book = self.client.Book.show(id)

        if self.book is None:
            self.logger.warn("No match found for ID: '%s'" % str(id))
        else:
            self.logger.info('Book found!')
        
        return self.book

    def search_title(self, title):
        """
        Search the Goodreads API for a book by its title.

        :param title: Goodreads title string
        :type title: str
        :return: book name
        :rtype: str
        """
        self.logger.info("Searching for title: '%s'" % str(title))
        self.book = self.client.Book.title(title)

        if self.book is None:
            self.logger.warn("No match found for title: '%s'" % str(title))
        else:
            self.logger.info('Book found!')

        return self.book

    def extract_all(self):
        """
        Return a dictionary with pre-defined keys of interest.

        :return: book data in dictionary with items: id, title, publication_year,
                 num_pages, language_code, country_code, description, average_rating,
                 url, ratings_count, text_reviews_count, 
        :rtype: dict
        """
        from html2text import html2text

        if self.book is None:
            errmsg = "Must run 'search_id()' or 'search_title()' first!"
            self.logger.error(errmsg)
            raise Exception(errmsg)

        items = [
            'id',
            'title',
            'publication_year',
            'num_pages',
            'language_code',
            'country_code',
            'description',
            'average_rating',
            'url',
            'ratings_count',
            'text_reviews_count'
        ]

        for item in items:
            if item in self.book.keys():
                self.bookdata[item] = self.book[item]
            else:
                self.logger.warn("Key '%s' missing from `self.bookdata`" % item)
                self.logger.debug("`item` = '%s'" % item)
                self.logger.debug("`type(item)` = '%s'" % type(item))
                self.logger.debug("`self.bookdata.keys()` = %s" % \
                    str(self.bookdata.keys()))

        if 'authors' in self.book.keys():
            if 'author' in self.book['authors'].keys():
                if 'name' in self.book['authors']['author'].keys():
                    self.bookdata['author'] = \
                        self.book['authors']['author']['name']
            else:
                self.logger.warn("Key 'author' missing from `self.book['authors']`")
        else:
            self.logger.warn("Key 'authors' missing from `self.bookdata`")

        if 'description' in self.bookdata.keys():
            desc = self.bookdata['description']
            desc = '' if desc is None else desc
            self.bookdata['description'] = html2text(desc).strip()
        else:
            self.logger.warn("Key 'description' missing from `self.bookdata`")

        return self.bookdata

    def as_data_frame(self):
        """
        Render `self.bookdata` dictionary as dataframe

        :return: book data as data frame
        :rtype: pd.DataFrame
        """
        import pandas as pd

        if not len(self.bookdata):
            errmsg = 'Must run `extract_all()` method first to populate ' \
            '`self.bookdata` dictionary!'
            self.logger.error(errmsg)
            raise Exception(errmsg)

        self.bookdf = pd.DataFrame(self.bookdata, index=0)
        self.logger.info('Coerced `self.bookdata` dictionary to dataframe')

        return self.bookdf
