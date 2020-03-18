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


class Movie(object):
    """
    Operate on a movie file.

    :param fname: path to movie file
    :type fname: str
    """
    
    def __init__(self, fname):

        import os
  
        assert os.path.isfile(fname)

        self.logger = pydoni.logger_setup(
            name=pydoni.what_is_my_name(classname=self.__class__.__name__, with_modname=True),
            level=pydoni.modloglev)

        self.fname = fname
        self.title = self.extract_from_fname(attr='title')
        self.year = self.extract_from_fname(attr='year')
        self.ext = self.extract_from_fname(attr='ext')
        
        # Will be set to True if self.query_omdb() is successful
        self.omdb_populated = False

        # Placeholder attributes that are filled in by class methods
        self.ratings = None
        self.rating_imdb = None
        self.rating_imdb = None
        self.rating_mc = None
        self.rating_rt = None
        self.imdb_rating = None
        self.metascore = None
    
    def extract_from_fname(self, attr=['title', 'year', 'ext']):
        """
        Extract movie title, year or extension from filename if filename is
        in format "${TITLE} (${YEAR}).${EXT}".
    
        :param fname {str}
        :desc filename to extract from, may be left as None if `self.fname` is already defined attr {str}
        :param attr {list}
        :desc attribute to extract, one of ['title', 'year', 'ext']
        :return: {str}
        """
        import re, os

        assert attr in ['title', 'year', 'ext']

        # Get filename
        fname = self.fname if hasattr(self, 'fname') else self.fname
        assert isinstance(fname, str)
        
        # Define movie regex
        rgx_movie = r'^(.*?)\((\d{4})\)'
        assert re.match(rgx_movie, self.fname)

        # Extract attribute
        movie = os.path.splitext(fname)[0]
        if attr == 'title':
            attrval = re.sub(rgx_movie, r'\1', movie).strip()
        elif attr == 'year':
            attrval = re.sub(rgx_movie, r'\2', movie).strip()
        elif attr == 'ext':
            attrval = os.path.splitext(fname)[1]

        self.logger.info("Extracted value '{}' for attribute '{}'".format(
            attr, str(attrval)))
        return attrval
        
    def query_omdb(self):
        """
        Query OMDB database from movie title and movie year.
        """
        import omdb

        try:
            met = omdb.get(title=self.title, year=self.year, fullplot=False, tomatoes=False)
            met = None if not len(met) else met
            
            if met is not None:
                for key, val in met.items():
                    setattr(self, key, val)
                
                self.parse_ratings()
                self.clean_omdb_response()
                self.omdb_populated = True

                self.logger.info("Successfully scraped OMDB for file '%s'" % self.fname)

            else:
                self.logger.error("Unable to find movie in OMDB database for file '%s'" % self.fname)
        
        except Exception as e:
            errmsg = 'OMDB API query failed for {}!'.format(self.fname)
            self.logger.error(errmsg)
            self.logger.error("Original error message:\n%s" % e.message)
            self.omdb_populated = False  # Query unsuccessful
    
    def parse_ratings(self):
        """
        Parse Metacritic, Rotten Tomatoes and IMDB User Ratings from the OMDB API's response.

        :param none
        :return: nothing
        """

        import numpy as np
        
        # Check that `self` has `ratings` attribute
        # Iterate over each type of rating (imdb, rt, mc) and assign to its own attribute
        # Ex: self.ratings['metacritic'] -> self.rating_mc
        if hasattr(self, 'ratings'):
            if len(self.ratings):
                for rating in self.ratings:
                    source = rating['source']
                    if source.lower() not in ['internet movie database', 'rotten tomatoes', 'metacritic']:
                        continue
                    source = re.sub('internet movie database', 'rating_imdb', source, flags=re.IGNORECASE)
                    source = re.sub('internet movie database', 'rating_imdb', source, flags=re.IGNORECASE)
                    source = re.sub('rotten tomatoes', 'rating_rt', source, flags=re.IGNORECASE)
                    source = re.sub('metacritic', 'rating_mc', source, flags=re.IGNORECASE)
                    source = source.replace(' ', '')
                    value = rating['value']
                    value = value.replace('/100', '')
                    value = value.replace('/10', '')
                    value = value.replace('%', '')
                    value = value.replace('.', '')
                    value = value.replace(',', '')
                    setattr(self, source, value)
                    self.logger.info("Set value '{}' for attribute '{}'".format(
                        str(value), str(source)))
            else:
                self.logger.error("`self` has attribute 'ratings' but it's empty!")    
        else:
            self.logger.error("`self` does not have attribute 'ratings'")
        
        # If one or more of the ratings were not present from OMDB
        # response, set to `np.nan`
        self.rating_imdb = np.nan if not hasattr(self, 'rating_imdb') else self.rating_imdb
        self.rating_rt   = np.nan if not hasattr(self, 'rating_rt') else self.rating_rt
        self.rating_mc   = np.nan if not hasattr(self, 'rating_mc') else self.rating_mc
        self.logger("Set `self` attributes: 'rating_imdb', 'rating_rt', 'rating_mc'")
        
        # Delete original ratings attributes now that each individual 
        # rating attribute has been established
        if hasattr(self, 'ratings'):
            del self.ratings
        if hasattr(self, 'imdb_rating'):
            del self.imdb_rating
        if hasattr(self, 'metascore'):
            del self.metascore

        self.logger.info('Deleted original ratings attributes from `self` (normal)')
    
    def clean_omdb_response(self):
        """
        Clean datatypes and standardize missing values from OMDB API response.
        """
        
        def convert_to_int(value):
            """
            Attempt to convert a value to type int.

            :param value {<> value to convert
            :type value: any
            :return: nothing
            """
            if isinstance(value, int):
                return value
            
            try:
                value = value.replace(',', '')
                value = value.replace('.', '')
                value = value.replace('min', '')
                value = value.replace(' ', '')
                value = value.strip()
                return int(value)
            except:
                return np.nan
        
        def convert_to_datetime(value):
            """
            Attempt to convert a value to type datetime.

            :param value {<> value to convert
            :type value: any
            :return: nothing
            """
            if not isinstance(value, str):
                return np.nan
            try:
                return datetime.strptime(value, '%d %b %Y').strftime('%Y-%m-%d')
            except:
                return np.nan

        def convert_to_bool(value):
            """
            Attempt to convert a value to type bool.

            :param value {<> value to convert
            :type value: any
            :return: nothing
            """
            if isinstance(value, str):
                if value.lower() in ['t', 'true']:
                    return True
                elif value.lower() in ['f', 'false']:
                    return False
                else:
                    return np.nan
            
            else:
                try:
                    return bool(value)
                except:
                    return np.nan
        
        # Convert attributes to integers if not already
        for attr in ['rating_imdb', 'rating_mc', 'rating_rt', 'imdb_votes', 'runtime']:
            if hasattr(self, attr):
                setattr(self, attr, convert_to_int(getattr(self, attr)))
        
        # Convert attributes to datetime if not already
        for attr in ['released', 'dvd']:
            if hasattr(self, attr):
                setattr(self, attr, convert_to_datetime(getattr(self, attr)))

        # Convert attributes to bool if not already
        for attr in ['response']:
            if hasattr(self, attr):
                setattr(self, attr, convert_to_bool(getattr(self, attr)))

        # Replace all N/A string values with `np.nan`
        self.replace_value('N/A', np.nan)
        self.logger.info('OMDB response cleaned!')
    
    def replace_value(self, value, replacement):
        """
        Scan all attributes for `value` and replace with `replacement` if found.
    
        :param value {<> value to search for
        :type value: any
        :param replacement {<> replace `value` with this variable value if found
        :type replacement: any
        :return: nothing
        """
        for key, val in self.__dict__.items():
            if val == value:
                setattr(self, key, replacement)
                self.logger.info("Replaced `self` attribute value '{}' with '{}'".format(
                    str(key), str(replacementm)))
