import pydoni
import pydoni.opsys
import pydoni.web


class Attribute(object):
    """
    General attribute to be used either as a standalone class in and of itself, or as an
    attribute to any external class.
    """

    def __init__(self):
        self.logger = pydoni.logger_setup(
            name=pydoni.what_is_my_name(classname=self.__class__.__name__, with_modname=True),
            level=pydoni.modloglev)

    def __flatten__(self):
        """
        Combine all subattributes of an Attribute. If all lists, flatten to single
        list. If all strings, join into a list.

        :return: flattened list
        :rtype: list
        """

        dct = self.__dict__
        is_list = list(set([True for k, v in dct.items() if isinstance(v, list)]))

        if len(is_list) == 0:
            # Assume string, no matches for isinstance(..., list)
            return [v for k, v in dct.items()]

        elif len(is_list) > 1:
            error_msg = 'Unable to flatten, varying datatypes (list, string, ...'
            self.logger.error(error_msg)
            raise Exception(error_msg)

        else:
            # Flatten list of lists
            lst_of_lst = [v for k, v in dct.items()]
            return [item for sublist in lst_of_lst for item in sublist]


class ProgramEnv(object):
    """
    Create, maintain, and erase a temporary program directory for a Python program.

    :param path: path to desired program environment directory
    :type path: str
    :param overwrite: remove `path` directory if already exists
    :type overwrite: bool
    """

    def __init__(self, path, overwrite=False):

        import os
        import shutil
        import click

        self.logger = pydoni.logger_setup(
            name=pydoni.what_is_my_name(classname=self.__class__.__name__, with_modname=True),
            level=pydoni.modloglev)

        # Assign program environment path
        self.path = path
        if self.path == os.path.expanduser('~') or self.path == '/':
            error_msg = 'Path cannot be home or root directory'
            self.logger.fatal(error_msg)
            raise Exception(error_msg)

        # self.focus is the current working file, if specified
        self.focus = None

        # Overwrite existing directory if specified and directory exists
        if os.path.isdir(self.path):
            if overwrite:
                shutil.rmtree(self.path)
            else:
                msg = "Specified path {} already exists and 'overwrite'".format(self.path) +\
                " set to False. Continue with this path anyway?"
                if not click.confirm(msg):
                    error_msg = 'Must answer affirmatively!'
                    self.logger.fatal(error_msg)
                    raise Exception(error_msg)

        # Create program environment
        if not os.path.isdir(self.path):
            os.mkdir(self.path)

    def copyfile(self, fname, set_focus=False):
        """
        Copy a file into the program environment.

        :param fname: filename to copy
        :type fname: str
        :param set_focus: set the focus to the newly copied file
        :type set_focus: bool

        :rtype: nothing
        """
        import os, shutil

        env_dest = os.path.join(self.path, os.path.basename(fname))
        shutil.copyfile(fname, env_dest)
        self.logger.info("Copied file '%s' to '%s'" % (fname, env_dest))
        if set_focus:
            self.focus = env_dest
            self.logger.info("Environment focus set to '%s'" % env_dest)

    def listfiles(
            self,
            path='.',
            pattern=None,
            full_names=False,
            recursive=False,
            ignore_case=True,
            include_hidden_files=False):
        """
        List files at given path.
        SEE `pydoni.listfiles()` FOR DETAILED DOCUMENTATION OF ARGUMENTS
        AND THEIR DATATYPES.
        """
        import os

        fnames = pydoni.listfiles(
            path=path,
            pattern=pattern,
            full_names=full_names,
            recursive=recursive,
            ignore_case=ignore_case,
            include_hidden_files=include_hidden_files)
        self.logger.info("Listed files at '%s', files found: %s" %  (os.getcwd(), str(len(fnames))))
        return fnames

    def listdirs(
            self,
            path='.',
            pattern=None,
            full_names=False,
            recursive=False):
        """
        List directories at given path.
        SEE `pydoni.opsys.listdirs()` FOR DETAILED DOCUMENTATION OF ARGUMENTS AND THEIR DATATYPES.
        """
        import os

        dnames = pydoni.listdirs(
            path=path,
            pattern=pattern,
            full_names=full_names,
            recursive=recursive)
        self.logger.info("Listed dirs at '%s', dirs found: %s" %  (os.getcwd(), str(len(dnames))))
        return dnames

    def downloadfile(self, url, destfile):
        """
        Download file from the web to a local file in Environment.

        :param url: target URL to retrieve file from
        :type url: str
        :param destfile: target filename
        :type destfile: str

        :rtype: {str}
        """
        pydoni.web.downloadfile(url=url, destfile=destfile)
        self.logger.info("Downloaded url '%s' to file '%s'" % (url, destfile))


    def unarchive(self, fpath, dest_dir):
        """
        Unpack a .zip archive.

        :param fpath: path to zip archive file
        :type fpath: str
        :param dest_dir: path to destination extract directory
        :type dest_dir: str

        :rtype: nothing
        """
        pydoni.opsys.unarchive(fpath=fpath, dest_dir=dest_dir)
        self.logger.info("Unarchived file '%s' to dir '%s'" % (fpath, dest_dir))

    def delete_env(self):
        """
        Remove environment from filesystem.
        """
        import os, shutil

        if os.path.isdir(self.path):
            self.logger.info("Deleting environment at '%s'" % self.path)
            os.chdir(os.path.dirname(self.path))
            shutil.rmtree(self.path)
            self.logger.info('Environment deleted')
        else:
            self.logger.warn("Could not find environment '%s' on filesystem, skipping" % self.path)


class DoniDt(object):
    """
    Custom date/datetime handling. Delete miliseconds by default.

    :param val >: value to consider for date/datetime handling, cast initially as string.
    :type val: any
    apply_tz {bool}  -- apply timezone value if present
            Ex: '2019-05-13 10:29:53-7:00' -> '2019-05-13 03:29:53'
    """

    def __init__(self, val, apply_tz=True):

        import os, re, datetime

        self.logger = pydoni.logger_setup(
            name=pydoni.what_is_my_name(classname=self.__class__.__name__, with_modname=True),
            level=pydoni.modloglev)

        self.val = str(val)
        sep = r'\.|\/|-|_|\:'

        # Assign regex expressions to match date, datetime,
        # datetime w/ time zone, and datetime w/ milliseconds
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

        none

        :rtype: {bool}
        """
        import re

        m = [bool(re.search(pattern, self.val)) for pattern in \
            ['^' + x + '$' for x in  self.rgx.__flatten__()]]
        out = any(m)
        self.logger.info("Value '%s' is%s exactly a date or datetime value" % \
            (str(self.val), ' not' if not out else ''))
        return out

    def contains(self):
        """
        Test if input string contains a date or datetime value.
        :rtype: {bool}
        """
        import re

        m = [bool(re.search(pattern, self.val)) for pattern in self.rgx.__flatten__()]
        out = any(m)
        self.logger.info("Value '%s' does%s contain a date or datetime value" % \
            (str(self.val), ' not' if not out else ''))
        return out

    def extract_first(self, apply_tz=True):
        """
        Given a string with a date or datetime value, extract the
        FIRST datetime value as string.

        :param apply_tz: apply timezone value if present
        :type apply_tz: bool
            Ex: '2019-05-13 10:29:53-7:00' -> '2019-05-13 03:29:53'
        """
        import datetime

        # Strip whitespace from value
        val = self.val.strip()

        # Only extract first dt value if any date/datetime value has been matched in string
        m = self.match
        if not self.match:
            self.logger.warn("Value '%s' does not match defined " % str(val) + \
                "date/datetime regex patterns. Returning initial value")
            return val

        # Extract date/datetime value based on value type
        if self.dtype == 'dt_tz':
            # Datetime with timezone

            # Build dt string
            dt = '{}-{}-{} {} --{} --{}'.format(
                m.group('year'), m.group('month'), m.group('day'),
                m.group('hours'), m.group('minutes'), m.group('seconds'))

            # Build timezone string
            tz = '{}{} --{}'.format(
                m.group('tz_sign'),
                m.group('tz_hours'),
                m.group('tz_minutes'))

            if apply_tz:
                tz = tz.split(':')[0]

                try:
                    tz = int(tz)
                except:
                    self.logger.error("Invalid timezone (not coercible to integer) '%s'" % tz)
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
        :rtype: {str}
        """
        import re

        if re.search(self.rgx.dt_tz, self.val):
            return ('dt_tz', re.search(self.rgx.dt_tz, self.val))
        elif re.search(self.rgx.dt, self.val):
            return ('dt', re.search(self.rgx.dt, self.val))
        elif re.search(self.rgx.d, self.val):
            return ('d', re.search(self.rgx.d, self.val))
        else:
            return (None, None)
