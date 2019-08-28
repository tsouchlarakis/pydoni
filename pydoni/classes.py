import bs4
import click
import datetime
import googlesearch
import numpy as np
import omdb
import requests
import shutil
import subprocess
import re
from datetime import datetime
from os import chdir, getcwd, mkdir, environ
from os.path import splitext, isfile, dirname, abspath, basename, isdir, expanduser, join
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


class Git(object):
    """
    House git command line function python wrappers.
    """

    def __init__(self):
        pass

    def status(self):
        """
        Return boolean based on output of 'git status' command. Return True if working tree is
        up to date and does not require commit, False if commit is required.
    
        Arguments:
            none
        
        Returns:
            {bool}
        """
        out = syscmd('git status').decode()
        working_tree_clean = "On branch masterYour branch is up to date with 'origin/master'.nothing to commit, working tree clean"
        not_git_repo = 'fatal: not a git repository (or any of the parent directories): .git'
        if out.replace('\n', '') == working_tree_clean:
            return True
        elif out.replace('\n', '') == not_git_repo:
            return None
        else:
            return False

    def add(self, fpath=None, all=False):
        """
        Add files to commit.
    
        Arguments:
            fpath (str or list): file(s) to add
            all   {bool}       : if True, execute 'git add .'
        
        Returns:
            nothing
        """
        if all == True and fpath is None:
            syscmd('git add .;', encoding='utf-8')
        elif isinstance(fpath, str):
            syscmd('git add "%s";' % fpath, encoding='utf-8')
        elif isinstance(fpath, list):
            for f in fpath:
                syscmd('git add "%s";' % f, encoding='utf-8')

    def commit(self, msg):
        """
        Execute 'git commit -m {}' where {} is commit message.
    
        Arguments:
            msg {str} -- commit message
        
        Returns:
            nothing
        """
        subprocess.call("git commit -m '{}';".format(msg), shell=True)

    def push(self):
        """
        Execute 'git push'.
    
        Arguments:
            none
        
        Returns:
            nothing
        """
        subprocess.call("git push;", shell=True)

    def pull(self):
        """
        Execute 'git pull'.
    
        Arguments:
            none
        
        Returns:
            nothing
        """
        subprocess.call("git pull;", shell=True)


class Song(object):
    """
    Gather metadata attributes of an .mp3 file

    Arguments:
        fname {str} -- path to .mp3 file
    """
    
    def __init__(self, fname):

        # File parameters
        self.fname = fname
        self.dname = dirname(abspath(self.fname))

        # Regex strings used in parsing title, album and/or track index from filename
        self.fname_rgx = r'^(\d+)\s*(.*?)\s*-\s*(.*?)(\.mp3)$'  # "01 Elvis Presley - Hound Dog.mp3"
        self.fname_rgx2 = r'^(\d+)\s*-?\s*(.*?)(\.mp3)$' # "01 - Hound Dog.mp3" OR "01 Hound Dog.mp3"
        
        # Run `exiftool` on music file
        self.exif = EXIF(fname).run(wrapper='doni')
        
        # Extract song-specific data
        self.title     = self.__get_song_title__()
        self.image     = self.__get_song_image__()
        self.track_raw = self.__get_song_track_raw__()
        self.track_idx = self.__get_song_track_idx__(self.track_raw)
        self.disc_raw  = self.__get_song_disc_raw__()
        self.disc_idx  = self.__get_song_disc_idx__(self.disc_raw)
        self.has_image = True if self.image is not None else False
        
        # Extract album-wide data
        self.artist = self.__get_song_artist__()
        self.album  = self.__get_song_album__()
        self.genre  = self.__get_song_genre__()
        self.year   = self.__get_song_year__()
        
        # Variables to access in this instance
        self.exitcodemap =  {
            0: 'Metadata successfully written',
            1: 'Ideal value does not exist, no change written',
            2: 'Ideal and current values are the same, no change written'
        }

    def __get_song_image__(self):
        """
        Get the image EXIF metadata.
        
        Returns:
            {str}
        """
        if 'picture' in self.exif.keys():
            return self.exif['picture']
        else:
            return None

    def __get_song_disc_raw__(self):
        """
        Get the raw disc EXIF metadata if it exists. Most likely it will not exist.
        
        Returns:
            {str}
        """
        if 'part_of_set' in self.exif.keys():
            return self.exif['part_of_set']
        else:
            return None

    def __get_song_disc_idx__(self, disc_raw):
        """
        Return the disc that a song appears in an album. Will generally be 1, but double and
        triple albums should be parsed as 2 and 3, respectively. Try to parse this from the
        filename, if the filename is in the format '2-01 Song Title Here.mp3'. In this case,
        the disc would be parsed as '2'. If not present, attempt to parse from directory
        name, as sometimes directory names contain 'CD 1' or 'Disc 2'. If not in either of
        those places, return nothing.
        
        Returns:
            {int}
        """

        if disc_raw is None:
            return 1

        # Check for disc index in exif
        if '/' in disc_raw:
            return disc_raw.split('/')[0]
        
        # Look for disc index in filename
        disc_rgx = r'(.*)(CD|Disc|Disk)(\b|\_|\s)(\d+)(.*)'
        if re.match(r'^\d-\d+ ', self.fname):
            return int(self.fname.split('-')[0])
        elif re.match(disc_rgx, self.dname):
            return int(re.sub(disc_rgx, r'\4', self.dname, flags=re.IGNORECASE))

        # Assign to default value of 1 if not found in exif of filename
        return 1

    def __get_song_track_raw__(self):
        """
        Get the raw track information in the EXIF metadata. If unavailable, attempt
        to parse from song filename.
        
        Returns:
            {str}
        """
        if 'track' in self.exif.keys():
            return self.exif['track']
        else:
            if re.match(self.fname_rgx, self.fname) or re.match(self.fname_rgx2, self.fname):
                track_raw = re.sub(self.fname_rgx, r'\1', self.fname).strip()
                try:
                    return int(track_raw)
                except:
                    return None
            else:
                return None

    def __get_song_track_idx__(self, track_raw):
        """
        Return the track index given the raw track metadata. Format will generally be a 
        single digit, or two digits, separated by a forward slash. Ex: '5', '9', '2/12'.
        Extract the 5, 9 and 2 respectively and convert to int.
        
        Returns:
            {int} or {None}
        """

        # No 'track' EXIF attribute, attempt to parse from filename
        if re.match(r'^\d+-\d+ ', self.fname):
            track_raw = re.sub(r'^(\d+)(-)(\d+) ', r'\3', self.fname)
        elif re.match(r'^\d{2} ', self.fname):
            track_raw = self.fname.split(' ')[0]
        else:
            return None

        # Convert to int. If can't convert to int, then invalid, so return None
        if track_raw.isdigit():
            return int(track_raw)
        elif re.match(r'^\d+\/\d+$', track_raw):
            return int(track_raw.split('/')[0])
        else:
            return None

    def __get_song_year__(self):
        """
        Parse the year from the directory (album) name.
        
        Returns:
            {int} or {None}
        """
        if re.match(r'(.*?)\((\d{4})\)', self.dname):
            year = re.sub(r'(.*?)(\(\[)(\d{4})(\)\])(.*)', r'\3', self.dname)
            year = int(year) if year.isdigit() else None
            return year
        
        elif re.match(r'^\d{4}', self.dname):
            year = re.sub(r'^(\d{4})(.*)', r'\1', self.dname)
            year = int(year) if year.isdigit() else None
            return year
        
        else:
            return None

    def __get_song_title__(self):
        """
        Attempt to parse song title from raw filename.
        
        Returns:
            {str} or {None}
        """

        # First check regex, then filename
        if 'title' in self.exif.keys():
            val = self.exif['title']
        elif re.match(self.fname_rgx, self.fname):
            val = re.sub(self.fname_rgx, r'\3', self.fname).strip()
        elif re.match(self.fname_rgx2, self.fname):
            val = re.sub(self.fname_rgx, r'\2', self.fname).strip()
        else:
            val = None

        # Clean title
        if val is not None:
            val = self.__generic_clean__(val)
            val = re.sub(r'(\w)(\/)(\w)', r'\1 \2 \3', val)
            return titlecase(val)
        else:
            return val

    def __get_song_artist__(self):
        """
        Attempt to parse song artist from raw filename.
        
        Returns:
            {str} or {None}
        """

        # First check EXIF metadata
        if 'artist' in self.exif.keys():
            val = self.exif['artist']
        elif re.match(self.fname_rgx, self.fname):
            val = re.sub(self.fname_rgx, r'\2', self.fname).strip()
        else:
            val = None
        
        if val is not None:
            if isinstance(val, str):
                if val > '':
                    val = self.__generic_clean__(val)
                    val = re.sub(r'(\w)( ?\/)(\w)', r'\1, \3', val)  # Replace slash with comma
                    return titlecase(val)
                else:
                    val = None
        
        return val

    def __get_song_album__(self):
        """
        Get EXIF album value and apply any corrections.
        
        Returns:
            {str}
        """

        if 'album' in self.exif.keys():
            val = self.exif['album']
            val = self.__generic_clean__(val)
            val = re.sub(r'(\w)(\/)(\w)', r'\1 \2 \3', val)
            val = val.replace('the', 'The')
            val = re.sub(r'^( *)(\[?)(\d{4})(\]?)( *)(-?|\.?)(.*)$', r'\7', val).strip()
            return val
        
        else:
            # No album attribute somehow, just assume directory name
            return dirname(self.dname)

    def __get_song_genre__(self):
        """
        Get song genre from EXIF metadata
        
        Returns:
            {str}
        """
        if 'genre' in self.exif.keys():
            val = self.exif['genre']
            val = self.__generic_clean__(val)
            val = val.replace('/', ', ')
            return val
        else:
            return None

    def __generic_clean__(self, val):
        """
        Apply general cleaning methods to any of the EXIF metadata attributes: artist,
        title, album, genre.
    
        Arguments:
            val {str} -- value to clean
        
        Returns:
            {str}
        """

        # Keep words that are all uppercase, generally acronyms. Titlecase will
        # convert all letters besides the first to lowercase
        keep_capital = [i for i, item in enumerate(val.split(' ')) if
                        item == item.upper() and re.match('[A-Z]+', item)]
        x = titlecase(val).split()  # Apply titlecase, then...
        if len(keep_capital):  # Keep words that are all capital that will be mutated by titlecase
            for idx in keep_capital:
                x[idx] = val.split(' ')[idx]

        # Make substitutions that have to do with common tags on the filenames of songs
        # These include "Bonus Track", "Remastered", "Alt Version", etc.
        # Replace so that these tags are enclosed in square brackets [] instead of
        # parenthesis () as they generally are.
        x = ' '.join(item for item in x)
        x = re.sub(r'\((Alternative|Alternate|Bonus) (Take|Track|Song)\)',
                   '[#]', x, flags=re.IGNORECASE)
        x = re.sub(r'\((Alternative|Alt|Version|ft|feat|featuring|with|Soundtrack|Remastered|Remaster|Remasterd|Remix|Unreleased)(.*)\)',
                   r'[\1\2]', x, flags=re.IGNORECASE)
        x = re.sub(r'\((.*?)(Alternative|Alt|Version|Unreleased)\)',
                   r'[\1\2]', x, flags=re.IGNORECASE)
        x = re.sub(r'\((\d{4}) (Remaster|Remastered|Remastrd|Remix)\)',
                   r'[\1 \2]', x, flags=re.IGNORECASE)
        x = re.sub(
            r'\((Remaster|Remastered|Remix) (\d{4})\)', r'\[\2 \1\]', x, flags=re.IGNORECASE)
        x = re.sub(r'\(Live\)', '[Live]', x, flags=re.IGNORECASE)
        x = re.sub(r'\] \[', '][', x)

        # General string cleaning primarily for song titles
        x = re.sub(r' +', ' ', x)
        x = x.replace('(#)', '[#]')
        x = x.replace('(*)', '[#]')
        x = x.replace('[*]', '[#]')
        x = x.replace("O'Er", "O'er")
        x = x.replace("'N'", "'n'")
        x = x.replace('[Ft', '[ft.')
        x = x.replace('[Ft.', '[ft.')
        x = x.replace('[Feat', '[ft.')
        x = x.replace('[Feat.', '[ft.')
        x = x.replace('[Featuring', '[ft.')
        x = x.replace('[Featuring.', '[ft.')
        x = x.replace('W / ', 'w/')
        x = x.replace('.mp3', '')
        x = x.replace('_', ' ')

        return x

    def set_exif(self, attr_name, attr_value):
        """
        Set song metadata field using mid3v2.
        
        Arguments:
            attr_name {str} -- name of attribute to set, must be one of ['artist', 'album', 'song', 'comment', 'picture', 'genre', 'year', 'date', 'track']
            attr_value {value} -- value of attribute to set
        
        Returns:
            {bool} or {str} -- True if successful, error message as string if unsuccessful
        """
        
        try:
            mid3v2(self.fname, attr_name=attr_name, attr_value=attr_value)
            return True
        except Exception as e:
            return  str(e)


class Album(object):
    """
    An Album datatype that will retrieve the relevant metadata attributes of an album by
    considering the metadata of all songs within the album.
    
    Arguments:
        dname {str} -- path to directory containing album of music files
    """

    def __init__(self, dname):

        # Navigate to target directory
        if basename(getcwd()) != dname:
            if isdir(dname):
                chdir(dname)
            else:
                echo("Cannot instantiate Album class because directory '{}' does not exist!".format(
                    dname), abort=True, fn_name='Album.__init__')

        # Get song files in directory
        self.dname = dname
        self.fnames = listfiles(ext=['mp3', 'flac'])
        if not len(self.fnames):
            echo("Cannot instantiate Album class because there are no mp3 or flac files found in directory '{}'!".format(
                self.dname), warn=True, fn_name='Album.__init__')

        # Loop over each song file and get album attributes:
        # album artist, album title, album year, album genre, number of tracks on disc
        if len(self.fnames):
            albuminfo = dict(
                artist    = [],
                title     = [],
                year      = [],
                genre     = [],
                songs     = [],
                has_image = []
            )
            songinfo = dict(
                title                = [],
                song_disc_idxs       = [],
                song_class_instances = []
            )
            track_raw_vals = []
            for fname in self.fnames:
                song = Song(fname)
                albuminfo['artist'].append(song.artist)
                albuminfo['title'].append(song.album)
                albuminfo['year'].append(song.year)
                albuminfo['genre'].append(song.genre)
                albuminfo['has_image'].append(song.has_image)
                songinfo['title'].append(song.title)
                songinfo['song_disc_idxs'].append(song.disc_idx)
                songinfo['song_class_instances'].append(song)
                track_raw_vals.append(song.track_raw)

            # Get number of discs in album
            self.disc_count = self.__get_discs_in_album__(
                songinfo['song_disc_idxs'])

            # Get number of tracks on disc
            self.track_total = self.__get_tracks_on_disc__(track_raw_vals)

            # Now condense all album attributes!

            # If multiple artists found in album, assume compilation album, and do
            # not alter artist
            if len(list(set(albuminfo['artist']))) == 1:
                self.artist = listmode(albuminfo['artist'])
            else:
                self.artist = albuminfo['artist']

            # Get most frequently-occurring year, genre and album title
            self.year  = listmode(albuminfo['year'])
            self.genre = listmode(albuminfo['genre'])
            self.title = listmode(albuminfo['title'])

            # If any songs have an image, set image indicator to True
            self.has_image = True if any(albuminfo['has_image']) else False

            # Set song-level information
            self.songs = songinfo['title']
            self.song_class_instances = songinfo['song_class_instances']

            # If any album attributes are None, attempt to correct using any means necessary
            if self.year is None:
                self.year = self.__get_year_from_dname__()

    def __get_discs_in_album__(self, song_disc_idxs):
        """
        Get the number of discs in album.
        
        Returns:
            {int}
        """

        # Get first from song disc indices
        discs = list(filter(None, list(set(song_disc_idxs))))
        discs = [x for x in discs if isinstance(x, int)]
        if len(discs) > 0:
            # There is disc information
            return max(discs)
        else:
            # No disc information from song disc indices, attempt to parse from filenames
            # of all files in album, then from directory name
            discs = []
            disc_dname_rgx = r'(.*)(CD|Disc|Disk)(\b|\_|\s)(\d+)(.*)'
            for fname in self.fnames:
                if re.match(r'^\d-\d+ ', fname):
                    # Filename matches for example '1-05 Test Song Name.mp3'. In this
                    # case, we want to extract the '1'.
                    return int(fname.split('-')[0])
                elif re.match(disc_dname_rgx, self.dname):
                    return int(re.sub(disc_dname_rgx, r'\4', self.dname, flags=re.IGNORECASE))
                else:
                    return 1

    def __get_tracks_on_disc__(self, track_raw_vals):
        """
        Return the total number of tracks in album. First check song raw track index
        metadata for total number of tracks. If not present, assume the total number
        of tracks on disc is equal to the total number of music files in directory.
    
        Arguments:
            trackraw_vals {list} -- list of trackraw values 
        
        Returns:
            {int}
        """
        if all([x is None for x in track_raw_vals]):
            return None

        track_denoms = []
        for x in track_raw_vals:
            if isinstance(x, str):
                if '/' in x:
                    track_denoms.append(x.split('/')[1])
        track_denoms = list(set(track_denoms))

        if len(track_denoms) == 1:
            track_total = track_denoms[0]
            if track_total.isdigit():
                return int(track_total)
            else:
                return len(self.fnames)

        elif len(track_denoms) > 1:
            # Multiple track denominators -> album has multiple tracks. Get the total
            # number of song files in directory
            return len(self.fnames)

        else:
            # 0 for denominator. Default to total number of song files in directory
            return len(self.fnames)

    def __get_year_from_dname__(self):
        """
        Attempt to extract album year from directory name.

        Returns:
            {int} or {None}
        """

        # Establish valid year ranges to check extracted year string against, from year
        # 1800 to current year plus one year
        valid_years = range(1800, int(datetime.datetime.now().strftime('%Y')) + 1)

        # First check first four characters of directory name for year. Often times
        # directory names will be in the format "YYYY ALBUM_TITLE"
        val = basename(self.dname)
        x = val[0:4]
        if x.isdigit():
            x = int(x)
            if x in valid_years:
                return x
        
        # Then check for year in parentheses or square brackets
        years = re.findall(r'\(\d{4}\)', val) + re.findall(r'\[\d{4}\]', val)
        if len(years):
            for x in years:
                x = re.sub(r'\(|\)|\[|\]', '', x)
                if x.isdigit():
                    x = int(x)
                    if x in valid_years:
                        return x

        # Then check in the entire directory name for four digits matching a valid year
        years = re.findall(r'\d{4}', val)
        if len(years):
            for x in years:
                if x.isdigit():
                    x = int(x)
                    if x in valid_years:
                        return x
        
        # If year still cannot be found, return None
        return None


    def scrape_wikipedia_genre(self, get_genre=True, get_image=True, image_outfile=None):
        """
        Find Wikipedia song link from Google to scrape for genre. If song page cannot
        be found or does not exist on Wikipedia, use the album's Wikipedia page. If that
        doesn't exist and genre is still unable to be found, return original genre. Also
        scrape image from same Wikipedia page.
        
        Keyword Arguments:
            get_genre {bool} -- if True, attempt to retrieve Wikipedia album genre (default: {True})
            get_image {bool} -- if True, attempt to retrieve Wikipedia album image (default: {True})
            image_outfile {str} -- path to desired image outfile from Wikipedia
        
        Returns:
            {str} -- genre string scraped from Wikipedia, may be comma-separated for multiple genres
        """

        def search_google_for_album_wikipage(artist, year, album):
            """
            Search Wikipedia for album URL.
            
            Arguments:
                artist {str} -- album artist
                year {str} -- album year
                album {str} -- album title
            
            Returns:
                {str} -- URL to Wikipedia page
            """
            clean_album = re.sub(
                r'(\[|\()(.*?)(\]|\))|CD\s*\d+|Disc\s*\d+', '', album, flags=re.IGNORECASE).strip()
            query = '{} {} {} album site:wikipedia.org'.format(
                artist, year, clean_album)
            wikilink = list(googlesearch.search(
                query, tld='com', num=1, stop=1, pause=2))
            if len(wikilink):
                return wikilink[0]
            else:
                return None

        def extract_genre_from_wikipage(wikilink):
            """
            Parse Wikipedia page HTML for album genre.
            
            Arguments:
                wikilink {str} -- link to Wikipedia page to scrape and
            
            Returns:
                {str} -- genre(s) parsed from Wikipedia page
            """


            # Scrape page for CSS selector
            genre = get_element_by_selector(wikilink, '.category a')
            if not len(genre) or not isinstance(genre, str):
                return None

            # Parse multiple genres if present
            genre = [genre] if isinstance(genre, str) else genre
            genre = [x for x in genre if not re.search(r'\[\d+\]', x)]
            if not len(genre):
                return None

            # Capitalize text for each genre returned
            genre = titlecase(', '.join(x for x in genre))
            return genre

        def extract_image_from_wikipage(wikilink, image_outfile, overwrite=True):
            """
            Parse Wikipedia page HTML for album image.
            
            Arguments:
                wikilink {str} -- link to Wikipedia page to scrape
                outfile {str} -- path to image outfile to save image to, if image is found
            
            Keyword Arguments:
                overwrite {bool} -- if True, overwrite `outfile` if it exists (default: {True})
            
            Returns:
                nothing
            """

            # Get image xpath
            img_xpath = get_element_by_xpath(
                wikilink, xpath='//*[contains(concat( " ", @class, " " ), concat( " ", "image", " " ))]//img/@src')
            if img_xpath is None or not len(img_xpath):
                return None
            else:
                img_xpath = img_xpath[0]

            # Extract image link from image xpath
            img_xpath = re.sub(r'thumb\/', '', img_xpath)
            img_xpath = re.sub(r'(.*?)(\.(jpg|jpeg|png)).*', r'\1\2', img_xpath)
            img_url = re.sub(r'^\/\/', 'https://', img_xpath)

            # Download image file to `outfile`
            outfile = splitext(image_outfile)[0] + splitext(img_url)[len(splitext(img_url))-1]
            if not isfile(outfile) or overwrite:
                downloadfile(img_url, outfile)

            return outfile

        def verify_downloaded_image(album_artwork_file):
                """
                Check if downloaded file is >1kb. Sometimes an image will be downloaded that is not
                a real image file.
                
                Arguments:
                    album_artwork_file {str} -- downloaded image file
                
                Returns:
                    {bool}
                """
                return int(stat(album_artwork_file)['Size']) > 1000

        # Execute steps used for getting both Genre and Image
        # Get wikipedia link
        wikilink = search_google_for_album_wikipage(
            self.artist, self.year, self.title)

        # Get Wikipedia link if possible and overwrite `self.genre` if scraping successful
        if get_genre:
            if requests.get(wikilink).status_code == 200:  # Webpage exists
                try:
                    parsed_genre = extract_genre_from_wikipage(wikilink)
                    if parsed_genre is not None:
                        # Overwrite genre
                        self.genre = parsed_genre
                        self.is_genre_from_wikipedia = True
                    else:
                        self.is_genre_from_wikipedia = False
                except:
                    # Scraping fails, do not overwrite genre
                    self.is_genre_from_wikipedia = False

        if get_image:
            # Get image by scraping Wikipedia page
            downloaded_file = extract_image_from_wikipage(wikilink, image_outfile)
            if isinstance(downloaded_file, str):
                if isfile(downloaded_file):
                    # Check that image is valid
                    if not verify_downloaded_image(downloaded_file):
                        if isfile(downloaded_file):
                            send2trash(downloaded_file)
                        else:
                            self.is_image_downloaded_from_wikipedia = False
                    else:
                        self.is_image_downloaded_from_wikipedia = True
                else:
                    self.is_image_downloaded_from_wikipedia = False
            else:
                self.is_image_downloaded_from_wikipedia = False


from pydoni.os import listdirs, listfiles, unarchive
from pydoni.pyobj import listmode, systime
from pydoni.sh import EXIF, mid3v2, stat, syscmd
from pydoni.vb import echo
from pydoni.web import downloadfile, get_element_by_selector, get_element_by_xpath