import goodreads_api_client as gr
import numpy as np
import omdb
import pandas as pd
import re
from html2text import html2text
from os.path import splitext


class Goodreads(object):
    """
    Extract Goodreads data for a title.

    Arguments:
        api_key {str} -- Goodreads API key string
    """

    def __init__(self, api_key):
        # self.api_key = 'XRdjRL9pCqTj4pUMyG1jyQ'
        # self.api_secret = '7zqBFszYrh3InYCMLZ2gyZXC1VPad2BELRWLXEU0bI'
        self.client = gr.Client(developer_key=api_key)
        self.book = None
        self.bookdata = {}
        self.bookdf = None

    def search_id(self, id):
        """
        Search the Goodreads API for a book by its ID.

        Arguments:
            id {str} -- Goodreads ID string
        """
        self.book = self.client.Book.show(id)
        return self.book

    def search_title(self, title):
        """
        Search the Goodreads API for a book by its title.

        Arguments:
            title {str} -- Goodreads title string
        """
        self.book = self.client.Book.title(title)
        return self.book

    def extract_all(self):
        """
        Return a dictionary with pre-defined keys of interest.
        """

        if self.book is None:
            echo("Must run 'search_id()' or 'search_title()' first!", abort=True)

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

        if 'authors' in self.book.keys():
            if 'author' in self.book['authors'].keys():
                if 'name' in self.book['authors']['author'].keys():
                    self.bookdata['author'] = \
                        self.book['authors']['author']['name']

        if 'description' in self.bookdata.keys():
            self.bookdata['description'] = \
                html2text(self.bookdata['description']).strip()

        return self.bookdata

    def as_data_frame(self):
        """
        Render `self.bookdata` dictionary as dataframe
        """
        if not len(self.bookdata):
            echo('Must run `extract_all()` method first to populate `self.bookdata` dictionary!', abort=True)

        self.bookdf = pd.DataFrame(self.bookdata, index=0)
        return self.bookdf


class Movie(object):
    """
    Operate on a movie file.

    Arguments:
        fname {str} -- path to audio file
    """
    
    def __init__(self, fname):
        self.fname          = fname
        self.title          = self.extract_from_fname(attr='title')
        self.year           = self.extract_from_fname(attr='year')
        self.ext            = self.extract_from_fname(attr='ext')
        self.omdb_populated = False  # Will be set to True if self.query_omdb() is successful

        # Placeholder attributes that are filled in by class methods
        self.ratings     = None
        self.rating_imdb = None
        self.rating_imdb = None
        self.rating_mc   = None
        self.rating_rt   = None
        self.imdb_rating = None
        self.metascore   = None
    
    def extract_from_fname(self, attr=['title', 'year', 'ext']):
        """
        Extract movie title, year or extension from filename if filename is
        in format "${TITLE} (${YEAR}).${EXT}".
    
        Arguments:
            fname {str} -- filename to extract from, may be left as None if `self.fname` is already defined
            attr {str} -- attribute to extract, one of ['title', 'year', 'ext']
        
        Returns:
            {str}
        """
        assert attr in ['title', 'year', 'ext']

        # Get filename
        fname = self.fname if hasattr(self, 'fname') else self.fname
        assert isinstance(fname, str)
        
        # Define movie regex
        rgx_movie = r'^(.*?)\((\d{4})\)'
        assert re.match(rgx_movie, self.fname)

        # Extract attribute
        movie = splitext(fname)[0]
        if attr == 'title':
            return re.sub(rgx_movie, r'\1', movie).strip()
        elif attr == 'year':
            return re.sub(rgx_movie, r'\2', movie).strip()
        elif attr == 'ext':
            return splitext(fname)[1]
        
    def query_omdb(self):
        """
        Query OMDB database from movie title and movie year.

        Arguments:
            none

        Returns:
            nothing
        """
        try:
            met = omdb.get(title=self.title, year=self.year, fullplot=False, tomatoes=False)
            met = None if not len(met) else met
            if met:
                for key, val in met.items():
                    setattr(self, key, val)
                self.parse_ratings()
                self.clean_omdb_response()
                self.omdb_populated = True
                # del self.title, self.year, self.ext
        except:
            echo('OMDB API query failed for {}!'.format(self.fname), error=True, abort=False)
            self.omdb_populated = False  # Query unsuccessful
    
    def parse_ratings(self):
        """
        Parse Metacritic, Rotten Tomatoes and IMDB User Ratings from the OMDB API's response.

        Arguments:
            none

        Returns:
            nothing
        """
        
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
        
        # If one or more of the ratings were not present from OMDB response, set to `np.nan`
        self.rating_imdb = np.nan if not hasattr(self, 'rating_imdb') else self.rating_imdb
        self.rating_rt   = np.nan if not hasattr(self, 'rating_rt') else self.rating_rt
        self.rating_mc   = np.nan if not hasattr(self, 'rating_mc') else self.rating_mc
        
        # Delete original ratings attributes now that each individual rating attribute has
        # been established
        if hasattr(self, 'ratings'):
            del self.ratings
        if hasattr(self, 'imdb_rating'):
            del self.imdb_rating
        if hasattr(self, 'metascore'):
            del self.metascore
    
    def clean_omdb_response(self):
        """
        Clean datatypes and standardize missing values from OMDB API response.

        Arguments:
            none

        Returns:
            nothing
        """
        
        def convert_to_int(value):
            """
            Attempt to convert a value to type int.

            Arguments:
                value {<any>} -- value to convert

            Returns:
                nothing
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

            Arguments:
                value {<any>} -- value to convert

            Returns:
                nothing
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

            Arguments:
                value {<any>} -- value to convert

            Returns:
                nothing
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
    
    def replace_value(self, value, replacement):
        """
        Scan all attributes for `value` and replace with `replacement` if found.ArithmeticError
    
        Arguments:
            value {<any>} -- value to search for
            replacement {<any>} -- replace `value` with this variable value if found
        
        Returns:
            nothing
        """
        for key, val in self.__dict__.items():
            if val == value:
                setattr(self, key, replacement)


from pydoni.vb import echo
