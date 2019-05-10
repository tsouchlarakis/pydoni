def syscmd(cmd, encoding=''):
    """
    Runs a command on the system, waits for the command to finish, and then
    returns the text output of the command. If the command produces no text
    output, the command's return code will be returned instead.
    Args
        cmd      (str): command string to execute
        encoding (str): [optional] name of decoding to decode output bytestring with
    Returns
        interned system output (str) or returncode (int)
    """
    import subprocess
    p = subprocess.Popen(
        cmd,
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        close_fds=True)
    p.wait()
    output = p.stdout.read()
    if len(output) > 1:
        if encoding:
            return output.decode(encoding)
        else:
            return output
    return p.returncode


def adobe_dng_converter(fpath, overwrite=False):
    """
    Run Adobe DNG Converter on a file.
    Args
        fpath     (str) : path to file
        overwrite (bool): if True, if output file already exists, overwrite it. if False, skip
    Returns
        nothing
    """
    from pydoni.vb import echo
    from pydoni.sh import syscmd
    from os.path import join, splitext, basename, isfile
    
    # Check if destination file already exists
    
    # Build output file with .dng extension and check if it exists
    destfile = join(splitext(fpath)[0], '.dng')
    exists = True if isfile(destfile) else False

    # Build system command
    app = join('/', 'Applications', 'Adobe DNG Converter.app', 'Contents', 'MacOS', 'Adobe DNG Converter')
    cmd = '"{}" "{}"'.format(app, fpath)
    
    # Execute command if output file does not exist, or if `overwrite` is True
    if exists:
        if overwrite:
            syscmd(cmd)
        else:
            # File exists but `overwrite` not specified as True
            echo('Destination file {} already exists'.format(destfile), warn=True)
    else:
        syscmd(cmd)


def stat(fname):
    """
    Call 'stat' UNIX command and parse output into a Python dictionary.
    Args
        fname (str): path to file
    Returns
        dict with items:
            File
            Size
            FileType 
            Mode
            Uid
            Device
            Inode
            Links
            AccessDate
            ModifyDate
            ChangeDate
    """
    from os.path import isfile
    from pydoni.sh import syscmd
    from pydoni.vb import echo, clickfmt
    
    def parse_datestring(fname, datestring):
        import datetime
        try:
            dt = datetime.datetime.strptime(datestring, '%a %b %d %H:%M:%S %Y')
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            from pydoni.vb import echo, clickfmt
            echo("Unable to parse date string {} for {} (original date string returned)". \
                    format(clickfmt(datestring, 'date'), clickfmt(fname, 'filename')), warn=True)
            return datestring
    
    # Check that filepath exists
    assert isfile(fname)

    # Build `stat` command
    cmd = 'stat -x "{}"'.format(fname)
    
    # Get output of `stat` command and clean for python list
    res = syscmd(cmd, encoding='utf-8')
    res = [x.strip() for x in res.split('\n')]
    
    # Parse out each element of `stat` output
    return dict(
        File       = res[0].split(':')[1].split('"')[1],
        Size       = res[1].split(':')[1].strip().split(' ')[0],
        FileType   = res[1].split(':')[1].strip().split(' ')[1],
        Mode       = res[2].split(':')[1].strip().split(' ')[0],
        Uid        = res[2].split(':')[2].replace('Gid', '').strip(),
        Device     = res[3].split(':')[1].replace('Inode', '').strip(),
        Inode      = res[3].split(':')[2].replace('Links', '').strip(),
        Links      = res[3].split(':')[3].strip(),
        AccessDate = parse_datestring(fname, res[4].replace('Access:', '').strip()),
        ModifyDate = parse_datestring(fname, res[5].replace('Modify:', '').strip()),
        ChangeDate = parse_datestring(fname, res[6].replace('Change:', '').strip()))


def mid3v2(fpath, attr_name, attr_value, quiet=True):
    """
    Use mid3v2 to add or overwrite a metadata attribute to a file.
    Args
        fpath      (str)       : path to file
        attr_name  (str)       : name of attribute to assign value to using mid3v2
        attr_value (str or int): value to assign to attribute `attr_name`
        quiet      (bool)      : if True, do not print any output to STDOUT
    Returns
        bool
    """
    from pydoni.sh import syscmd
    from pydoni.vb import echo

    # Check that attribute name is valid
    valid = ['artist', 'album', 'song', 'comment', 'picture', 'genre', 'year', 'date', 'track']
    assert attr_name in valid

    # Build command
    cmd = 'mid3v2 --{}="{}" "{}"'.format(attr_name, attr_value, fpath)

    # Execute command
    try:
        if quiet:
            out = syscmd(cmd)
        else:
            syscmd(cmd)
        return True
    except Exception as e:
        echo('failed', error=True, erro_msg=str(e), fn_name='mid3v2')
        return False
    
