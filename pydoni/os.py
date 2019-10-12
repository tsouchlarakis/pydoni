import re
import zipfile
from os import getcwd, walk, listdir, getcwd, chdir, name as os_name
from os.path import isdir, isfile, expanduser, join, basename, splitext


class FinderMacOS(object):
    """
    MacOS Finder object. Holds functions to carry out Finder operations on a file or directory.
    
    Arguments:
        fpath {str} -- path to file
    """
    def __init__(self, fpath):
        if not isfile(fpath):
            echo("Specified filepath '{}' does not exist!".format(fpath), abort=True)
        self.fpath = fpath
    
    def get_comment(self):
        """
        Call `mdls` BASH command to retrieve a file's Finder comment on macOS.
        
        Arguments:
            none

        Returns:
            {str}
        """
        self.__assert_fpath__()
        cmd = 'mdls -r -nullMarker "" -n kMDItemFinderComment "%s"' % self.fpath
        res = syscmd(cmd, encoding='utf-8')
        if 'could not find ' + basename(self.fpath) in res:
            res = ''
        return res

    def write_comment(self, comment):
        """
        Use Applescript to write a Finder comment to a file.
        
        Arguments:
            comment {str} -- comment string to write to file
        
        Returns:
            {bool}
        """
        self.__assert_fpath__()

        # First clear the comment field, then write new value
        cmd = '/usr/bin/osascript -e'
        applescript = 'set filepath to POSIX file "{}"\nset the_file to filepath as alias\ntell application "Finder" to set the comment of the_file to "{}"'
        applescript_clear = applescript.format(self.fpath, 'test')
        applescript_set = applescript.format(self.fpath, comment)
        applescript_clear = re.sub(r'"', r'\"', applescript_clear)
        applescript_set = re.sub(r'"', r'\"', applescript_set)
        try:
            res = syscmd(cmd + ' "' + applescript_clear + '"')
            res = syscmd(cmd + ' "' + applescript_set + '"')
            return True
        except:
            return False

    def remove_comment(self):
        """
        Use Applescript to remove a file's Finder comment.
        
        Arguments:
            none

        Returns:
            {bool}
        """
        self.__assert_fpath__()
        
        # Remove finder comment by setting to ''
        cmd = '/usr/bin/osascript -e'
        applescript = 'set filepath to POSIX file "%s"\nset the_file to filepath as alias\ntell application "Finder" to set the comment of the_file to ""' % self.fpath
        applescript = re.sub(r'"', r'\"', applescript)
        try:
            os.system(cmd + ' "' + applescript + '"')
            return True
        except:
            return False

    def get_tag(self):
        """
        Parse `mdls` output to get a file's Finder tags.
        
        Arguments:
            none

        Returns:
            {list}
        """
        self.__assert_fpath__()
        cmd = 'mdls -r -nullMarker "" -n kMDItemUserTags "%s"' % self.fpath
        tags = str(syscmd(cmd, encoding='utf-8'))
        if tags == '0':
            return []
        tags = [x.strip() for x in tags.split('\n') if '(' not in x and ')' not in x]
        tags = [x.replace(',', '') for x in tags]
        tags = [tags] if isinstance(tags, str) else tags
        return tags

    def write_tag(self, tag):
        """
        Write Finder tag or tags to a file. Requires Jdberry's 'tag' command line utility to
        be installed. Install here: https://github.com/jdberry/tag
        
        Arguments:
            tag {str} or {list} -- string or list of finder tags. Usually one or more of 'Red', 'Orange', 'Yellow', ...
        
        Returns:
            {bool}
        """
        tag = [tag] if isinstance(tag, str) else tag
        res = []
        for tg in tag:
            z = syscmd('tag --add "%s" "%s"' % (tg, self.fpath))
            res.append(z)
        if len(list(set(res))) == 1:
            if list(set(res)) == [0]:
                return True
            else:
                return False
        else:
            return False

    def remove_tag(self, tag):
        """
        Remove a Finder tag or tags from a file. Requires Jdberry's 'tag' command line utility to
        be installed. Install here: https://github.com/jdberry/tag
        
        Arguments:
            tag {str} or {list} -- name(s) of Finder tags to remove
        
        Returns:
            {bool}
        """
        
        if tag == 'all':
            tag = self.get_tag()
        elif isinstance(tag, str):
            tag = [tag]
        
        res = []
        for tg in tag:
            z = syscmd('tag --remove "%s" "%s"' % (tg, self.fpath))
            res.append(z)
        
        if len(list(set(res))) == 1:
            if list(set(res)) == [0]:
                return True
            else:
                return False
        else:
            return False
    
    def __assert_fpath__(self):
        if not isfile(self.fpath):
            echo("`self.fpath` '{}' no longer exists!".format(self.fpath),
                fn_name='FinderMacOS.*', abort=True)


def listfiles(
    path                 = '.',
    pattern              = None,
    ext                  = None,
    full_names           = False,
    recursive            = False,
    ignore_case          = True,
    include_hidden_files = False
    ):
    """
    List files in a given directory.
    
    Keyword Arguments:
        path {str} -- directory path in which to search for files (default: {'.'})
        pattern {str} -- if specified, filter resulting files by matching regex pattern (default: {None})
        ext {str} or {list} -- extention or list of extensions to filter resulting files by (default: {None})
        full_names {bool} -- if True, return full filepath from current directory instead of just the file's basename (default: {False})
        recursive {bool} -- if True, search recursively down the directory tree for files (default: {False})
        ignore_case {bool} -- if True, use re.IGNORECASE flag when filtering files by regex specified in `pattern` parameter (default: {True})
        include_hidden_files {bool} -- if True, include hidden files in resulting file list (default: {False})
    
    Returns:
        {list} -- list of files
    """

    assert isdir(path)

    # Change to specified directory and record original directory to change back to at the end
    wd = getcwd()
    chdir(path)

    # List files, either recursively or not recursively
    if recursive:
        fnames = [join(dp, f).replace('./', '') \
            for dp, dn, filenames in walk('.') \
            for f in filenames]
    else:
        fnames = listdir()
    fnames = [f for f in fnames if isfile(f)]
    
    # Filter out hidden files if specified
    if not include_hidden_files:
        fnames = [fname for fname in fnames if not basename(fname).startswith('.')]
    
    # If a regex pattern is specified, filter file list by that pattern
    if pattern is not None:
        if ignore_case:
            fnames = [x for x in fnames if re.search(pattern, x, re.IGNORECASE)]
        else:
            fnames = [x for x in fnames if re.search(pattern, x)]
    
    # If an extension or list of extensions is specified, filter resulting file list by
    # that extension or those extensions
    if ext:
        ext = [ext] if isinstance(ext, str) else ext
        ext = [x.lower() for x in ext]
        ext = ['.' + x if not x.startswith('.') else x for x in ext]
        fnames = [x for x in fnames if splitext(x)[1].lower() in ext]
    
    # Specify full name from current directory down if specified by joining the current
    # directory onto each filename
    if full_names:
        path_expand = getcwd() if path == '.' else path
        fnames = [join(path_expand, fname) for fname in fnames]
    
    # Change back to original directory
    chdir(wd)

    # Return sorted list of files
    return sorted(fnames)


def listdirs(path='.', pattern=None, full_names=False, recursive=False):
    """
    List subdirectories in a given directory.
    
    Keyword Arguments:
        path {str} -- directory path in which to search for subdirectories
        pattern {str} -- if specified, filter resulting dirs by matching regex pattern
        full_names {bool} -- if True, return full directory path from current directory instead of just the directory's basename
        recursive {bool} -- if True, search recursively down the directory tree for files
    
    Returns:
        {list} -- list of directories
    """

    # Check if specified path exists
    if not isdir(path):
        echo("Path '{}' does not exist".format(path), fn_name='listdirs', error=True)
        return None

    # Change to specified directory and record original directory to change back to at the end
    wd = getcwd()
    chdir(path)

    # List directories either recursively or not
    if recursive:
        dnames = [join(root, subdir).replace('./', '') \
            for root, subdirs, filenames in walk('.') \
            for subdir in subdirs]
    else:
        dnames = next(walk(path))[1]
        dnames = sorted(dnames)
    
    # Specify full name from current directory down if specified by joining the current
    # directory onto each dirname
    if full_names:
        path_expand = getcwd() if path == '.' else path
        dnames = [join(path_expand, dname) for dname in dnames]
    
    # If a regex pattern is specified, filter directory list by that pattern
    if pattern is not None:
        dnames = [x for x in dnames if re.match(pattern, x)]
    
    # Change back to original directory
    chdir(wd)

    # Return sorted list of dirs
    return sorted(dnames)


def assert_dpath(dpaths=[], abort=True):
    """
    Check that a given path or paths exist. Optional abort program if one or more directories
    do not exist.
    
    Keyword Arguments:
        dpaths {str} or {list} -- directory path(s) to check for existence
        abort {bool} -- if True, `quit()` will be executed if one or more directories do not exist
    
    Returns:
        {bool}
    """
    
    # Expand directory paths
    if not isinstance(dpaths, list):
        dpaths = [dpaths]
    dpaths = [expanduser(x) for x in dpaths]

    # Test whether each directory exists
    res = []
    for dpath in dpaths:
        if isdir(dpath):
            res.append((dpath, True))
        else:
            res.append((dpath, False))
    
    # Print directories that do not exist to the screen
    for dname, exists in res:
        if not exists:
            echo("Directory '{}' does not exist!".format(dname), error=True)
    
    # Determine return condition or if program should exit
    if all([exists for dname, exists in res]):
        # All directories exist
        return True
    else:
        if abort:
            quit()
        else:
            return False


def unarchive(fpath, dest_dir):
    """
    Unpack a .zip archive.
    
    Arguments:
        fpath {str} -- path to zip archive file
        dest_dir {str} -- path to destination extract directory
    
    Returns:
        nothing
    """
    with zipfile.ZipFile(fpath, 'r') as zip_ref:
        zip_ref.extractall(dest_dir)


def macos_notify(title='', subtitle=None, message='', app_icon=None, content_image=None, command=None, open_iterm=False):
    """
    Python wrapper for julienXX's terminal-notifier gem found here:
    https://github.com/julienXX/terminal-notifier
    
    Keyword Arguments:
        title         {str} -- title string for notification
        subtitle      {str} -- subtitle string for notification
        message       {str} -- message string for notification
        app_icon      {str} -- path to image file to display instead of application icon
        content_image {str} -- path to image file to attach inside of notification
        command       {str} -- shell command string to execute when notification is clicked
        open_iterm   {bool} -- overwrites 'command' parameter as 'open /Applications/iTerm.app'
    
    Returns:
        nothing
    """

    assert message > ''

    # Check that terminal-notifier is installed
    tnv = syscmd('which terminal-notifier').decode().strip()
    if not isfile(tnv):
        echo("terminal-notifier is not installed! Please install it per instructions at https://github.com/julienXX/terminal-notifier", abort=True)

    # Check that operating system is macOS
    if os_name.lower() != 'posix':
        echo('Operating system is not macOS!', abort=True)

    # Build list of arguments for terminal-notifier and check that each parameter is valid
    cl_string = []
    if title is not None:
        assert isinstance(title, str)
        cl_string.append('-title {!r}'.format(title))
    if subtitle is not None:
        assert isinstance(subtitle, str)
        cl_string.append('-subtitle {!r}'.format(subtitle))
    if message is not None:
        assert isinstance(message, str)
        cl_string.append('-message {!r}'.format(message))
    if app_icon is not None:
        assert isinstance(app_icon, str)
        assert isfile(app_icon)
        cl_string.append('-appIcon {!r}'.format(app_icon))
    if content_image is not None:
        assert isinstance(content_image, str)
        assert isfile(content_image)
        cl_string.append('-contentImage {!r}'.format(content_image))
    assert isinstance(open_iterm, bool)
    if open_iterm:
        cl_string.append("-execute 'open /Applications/iTerm.app'")
    elif command is not None:
        assert isinstance(command, str)
        cl_string.append('-execute {!r}'.format(command))
    
    # Build final command and execute
    cmd = 'terminal-notifier {}'.format(' '.join(cl_string))
    syscmd(cmd)


from pydoni.sh import syscmd
