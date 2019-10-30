import click
import datetime
import numpy as np
import re
import shutil
from os import chdir
from os import environ
from os import listdir
from os import mkdir
from os.path import basename
from os.path import dirname
from os.path import expanduser
from os.path import join
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
from pydoni.vb import echo
from pydoni.web import downloadfile
