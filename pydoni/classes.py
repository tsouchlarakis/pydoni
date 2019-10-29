import bs4
import click
import datetime
import googlesearch
import numpy as np
import omdb
import re
import requests
import shutil
import subprocess
from os import chdir
from os import environ
from os import getcwd
from os import listdir
from os import mkdir
from os.path import abspath
from os.path import basename
from os.path import dirname
from os.path import expanduser
from os.path import isdir
from os.path import isfile
from os.path import join
from os.path import splitext
from send2trash import send2trash
from titlecase import titlecase
from tqdm import tqdm


class Attribute(object):
    """
    General attribute to be used either as a standalone class in and of itself, or as an
    attribute to any external class.
    """

    def __init__(self):
        pass

    def __flatten__(self):
        """
        Combine all subattributes of an Attribute. If all lists, flatten to single
        list. If all strings, join into a list.

        Returns:
            {list}
        """
        
        dct = self.__dict__
        is_list = list(set([True for k, v in dct.items() if isinstance(v, list)]))
        
        if len(is_list) == 0:
            # Assume string, no matches for isinstance(..., list)
            return [v for k, v in dct.items()]

        elif len(is_list) > 1:
            print('ERROR: Unable to flatten, varying datatypes (list, string, ...)')
            return None

        else:
            # Flatten list of lists
            lst_of_lst = [v for k, v in dct.items()]
            return [item for sublist in lst_of_lst for item in sublist]


class ProgramEnv(object):
    """
    Create, maintain, and erase a temporary program directory for a Python program.

    Arguments:
        path {str}  -- path to desired program environment directory
        overwrite {bool} -- if True, remove `path` directory if already exists
    """

    def __init__(self, path, overwrite=False):
        
        # Assign program environment path
        self.path = path
        if self.path == expanduser('~'):
            echo('Path cannot be home directory', abort=True)
        elif self.path == '/':
            echo('Path cannot be root directory', abort=True)
        
        # self.focus is the current working file, if specified
        self.focus = None
        
        # Overwrite existing directory if specified and directory exists
        if isdir(self.path):
            if overwrite:
                shutil.rmtree(self.path)
            else:
                if not click.confirm("Specified path {} already exists and 'overwrite' set to False. Continue with this path anyway?".format(self.path)):
                    echo('Must answer affirmatively!', abort=True)
        
        # Create program environment
        if not isdir(self.path):
            mkdir(self.path)
    
    def copyfile(self, fname, set_focus=False):
        """
        Copy a file into the program environment.
    
        Arguments:
            fname {str} -- filename to copy
            set_focus {bool} -- if True, set the focus to the newly copied file
        
        Returns:
            nothing
        """
        env_dest = join(self.path, basename(fname))
        shutil.copyfile(fname, env_dest)
        if set_focus:
            self.focus = env_dest
    
    def listfiles(self, path='.', pattern=None, full_names=False, recursive=False, ignore_case=True, include_hidden_files=False):
        """
        List files at given path.
        SEE `pydoni.listfiles()` FOR DETAILED DOCUMENTATION OF ARGUMENTS AND THEIR DATATYPES.
        """
        return listfiles(path=path, pattern=pattern, full_names=full_names,
            recursive=recursive, ignore_case=ignore_case,
            include_hidden_files=include_hidden_files)
    
    def listdirs(self, path='.', pattern=None, full_names=False, recursive=False):
        """
        List directories at given path.
        SEE `pydoni.listdirs()` FOR DETAILED DOCUMENTATION OF ARGUMENTS AND THEIR DATATYPES.
        """
        return listdirs(path=path, pattern=pattern, full_names=full_names, recursive=recursive)
    
    def downloadfile(self, url, destfile):
        """
        Download file from the web to a local file in Environment.
    
        Arguments:
            url {str} -- target URL to retrieve file from
            destfile {str} -- target filename
        
        Returns:
            {str}
        """
        downloadfile(url=url, destfile=destfile)
    

    def unarchive(self, fpath, dest_dir):
        """
        Unpack a .zip archive.
    
        Arguments:
            fpath {str} -- path to zip archive file
            dest_dir {str} -- path to destination extract directory
        
        Returns:
            nothing
        """
        unarchive(fpath=fpath, dest_dir=dest_dir)

    def delete_env(self):
        """
        Remove environment from filesystem.
        """
        if isdir(self.path):
            chdir(dirname(self.path))
            shutil.rmtree(self.path)


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
                return int(value.replace(',', '').replace('.', '').replace('min', '').replace(' ', '').strip())
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


class DoniDt(object):
    """
    Custom date/datetime handling. Delete miliseconds by default.

    Arguments:
        val {<any>} -- value to consider for date/datetime handling, cast initially as string.
        apply_tz {bool}  -- if True, apply timezone value if present
            Ex: '2019-05-13 10:29:53-7:00' -> '2019-05-13 03:29:53'
    """

    def __init__(self, val, apply_tz=True):
        
        self.val = str(val)
        sep = r'\.|\/|-|_|\:'
        
        # Assign regex expressions to match date, datetime, datetime w/ time zone, and
        # datetime w/ milliseconds
        rgx = Attribute()
        rgx.d = r'(?P<year>\d{4})(%s)(?P<month>\d{2})(%s)(?P<day>\d{2})' % (sep, sep)
        rgx.dt = r'%s(\s+)(?P<hours>\d{2})(%s)(?P<minutes>\d{2})(%s)(?P<seconds>\d{2})' % (rgx.d, sep, sep)
        rgx.dt_tz = r'%s(?P<tz_sign>-|\+)(?P<tz_hours>\d{1,2})(:)(?P<tz_minutes>\d{1,2})' % (rgx.dt)
        rgx.dt_ms = r'%s\.(?P<miliseconds>\d+)$' % (rgx.dt)
        self.rgx = rgx
        
        # Parse type as one of above date types
        self.dtype, self.match = self.detect_dtype()
    
    def is_exact(self):
        """
        Test if input string is exactly a date or datetime value.
        
        Arguments:
            none

        Returns:
            {bool}
        """
        m = [bool(re.search(pattern, self.val)) for pattern in \
            ['^' + x + '$' for x in  self.rgx.__flatten__()]]
        return any(m)
    
    def contains(self):
        """
        Test if input string contains a date or datetime value.

        Arguments:
            none
        
        Returns:
            {bool}
        """
        m = [bool(re.search(pattern, self.val)) for pattern in self.rgx.__flatten__()]
        return any(m)
    
    def extract_first(self, apply_tz=True):
        """
        Given a string with a date or datetime value, extract the FIRST datetime value as string.

        Arguments:
            none
    
        Arguments:
            apply_tz {bool} -- if True, apply timezone value if present
                Ex: '2019-05-13 10:29:53-7:00' -> '2019-05-13 03:29:53'
        """

        # Strip whitespace from value
        val = self.val.strip()

        # Only extract first dt value if any date/datetime value has been matched in string
        m = self.match
        if not self.match:
            return val

        # Extract date/datetime value based on value type
        if self.dtype == 'dt_tz':
            # Datetime with timezone
            
            # Build dt string
            dt = '{}-{}-{} {} --{} --{}'.format(
                m.group('year'), m.group('month'), m.group('day'),
                m.group('hours'), m.group('minutes'), m.group('seconds'))
            
            # Build timezone string
            tz = '{}{} --{}'.format(m.group('tz_sign'), m.group('tz_hours'), m.group('tz_minutes'))
            
            if apply_tz:
                tz = tz.split(':')[0]
                
                try:
                    tz = int(tz)
                except:
                    echo("Invalid timezone (no coercible to integer) '{}'".format(tz),
                        error=True, fn_name='DoniDt.extract_first')
                    self.dtype = 'dt'
                    return dt
                
                dt = datetime.datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
                dt = dt + datetime.timedelta(hours=tz)
                self.dtype = 'dt_tz'
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                # Change value type to datetime
                self.dtype = 'dt'
                return dt

        elif self.dtype == 'dt':
            # Datetime
            dt = '{}-{}-{} {} --{} --{}'.format(
                m.group('year'), m.group('month'), m.group('day'),
                m.group('hours'), m.group('minutes'), m.group('seconds'))
            self.dtype = 'dt'
            return dt

        elif self.dtype == 'd':
            # Date
            dt = '{}-{}-{}'.format(m.group('year'), m.group('month'), m.group('day'))
            self.dtype = 'd'
            return dt
    
    def detect_dtype(self):
        """
        Get datatype as one of 'd', 'dt', 'dt_tz', and return regex match object.

        Arguments:
            none
        
        Returns:
            {str}
        """
        if re.search(self.rgx.dt_tz, self.val):
            return ('dt_tz', re.search(self.rgx.dt_tz, self.val))
        elif re.search(self.rgx.dt, self.val):
            return ('dt', re.search(self.rgx.dt, self.val))
        elif re.search(self.rgx.d, self.val):
            return ('d', re.search(self.rgx.d, self.val))
        else:
            return (None, None)


from pydoni.os import listdirs
from pydoni.os import listfiles
from pydoni.os import unarchive
from pydoni.pyobj import listmode
from pydoni.pyobj import systime
from pydoni.sh import EXIF
from pydoni.sh import mid3v2
from pydoni.sh import stat
from pydoni.sh import syscmd
from pydoni.vb import echo
from pydoni.web import downloadfile
from pydoni.web import get_element_by_selector
from pydoni.web import get_element_by_xpath