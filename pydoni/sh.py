def syscmd(cmd, encoding=''):
    """Runs a command on the system, waits for the command to finish, and then
    returns the text output of the command. If the command produces no text
    output, the command's return code will be returned instead."""
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

def exiftool(filepath, rmtags=None, attr_name=None):
    import subprocess, re
    from pydoni.sh import syscmd
    if rmtags:
        if isinstance(rmtags, str):
            res = syscmd('exiftool -overwrite_original -{}= "{}"'.format(rmtags, filepath))
        elif isinstance(rmtags, list):
            for tag in remove_tags:
                res = syscmd('exiftool -overwrite_original -{}= "{}"'.format(tag, filepath))
        else:
            echo("Parameter 'rmtags' must be of type str or list", fn_name='exiftool', abort=True)
        return None
    # Normal call to this function
    res = subprocess.run('exiftool "%s"' % filepath, stdout=subprocess.PIPE, shell=True)
    res = str(res.stdout.decode('utf-8', errors='backslashreplace'))
    exif = [x for x in res.split('\n') if x > '']
    keys = [re.sub(r'^(.*?)(:)(.*)$', r'\1', x).strip() for x in exif]
    vals = [re.sub(r'^(.*?)(:)(.*)$', r'\3', x).strip() for x in exif]
    exif_dict = dict(zip(keys, vals))
    exif_dict = {k.lower().replace(' ', '_'): v for k, v in exif_dict.items()}
    if attr_name:  # Filter result
        if isinstance(attr_name, str):
            attr_name = [attr_name]
        return {key: exif_dict[key] for key in attr_name}
    else:
        return exif_dict

def adobe_dng_converter(fpath, overwrite=False):
    """Run Adobe DNG Converter on a file"""
    from pydoni.vb import echo
    from pydoni.sh import syscmd
    from os.path import join, splitext, basename, isfile
    # Check if destination file already exists
    destfile = join(splitext(fpath)[0], '.dng')
    app = join('/', 'Applications', 'Adobe DNG Converter.app', 'Contents', 'MacOS', 'Adobe DNG Converter')
    cmd = '"{}" "{}"'.format(app, fpath)
    if isfile(destfile):
        if overwrite:
            syscmd(cmd)
        else:
            echo('Destination file {} already exists'.format(destfile), warn=True)
    else:
        syscmd(cmd)

def stat(fname):  # Call 'stat' UNIX command and parse output into a Python dictionary
    import os
    from pydoni.sh import syscmd
    from pydoni.vb import echo, clickfmt
    def parseDatestring(fname, datestring):
        import datetime
        try:
            dt = datetime.datetime.strptime(datestring, '%a %b %d %H:%M:%S %Y')
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            from pydoni.vb import echo, clickfmt
            echo("Unable to parse date string {} for {} (original date string returned)". \
                    format(clickfmt(datestring, 'date'), clickfmt(fname, 'filename')), warn=True)
            return datestring
    if not os.path.isfile(fname):
        echo('No such file or directory {}'.format(clickfmt(fname, 'filename')), error=True)
        return None
    cmd = 'stat -x "{}"'.format(fname)
    res = syscmd(cmd).decode('utf-8')
    res = [x.strip() for x in res.split('\n')]
    return dict(
        File       = res[0].split(':')[1].split('"')[1],
        Size       = res[1].split(':')[1].strip().split(' ')[0],
        FileType   = res[1].split(':')[1].strip().split(' ')[1],
        Mode       = res[2].split(':')[1].strip().split(' ')[0],
        Uid        = res[2].split(':')[2].replace('Gid', '').strip(),
        Device     = res[3].split(':')[1].replace('Inode', '').strip(),
        Inode      = res[3].split(':')[2].replace('Links', '').strip(),
        Links      = res[3].split(':')[3].strip(),
        AccessDate = parseDatestring(fname, res[4].replace('Access:', '').strip()),
        ModifyDate = parseDatestring(fname, res[5].replace('Modify:', '').strip()),
        ChangeDate = parseDatestring(fname, res[6].replace('Change:', '').strip()))

def mid3v2(fpath, attr_name, attr_value, quiet=True):
    # Use mid3v2 to add or overwrite a metadata attribute to a file
    from pydoni.sh import syscmd
    from pydoni.vb import echo
    valid_attr_name = ['artist', 'album', 'song', 'comment', 'picture', 'genre', 'year', \
        'date', 'track']
    if not isinstance(attr_name, str):
        echo('mid3v2 attribute name must be of type string', abort=True)
    if attr_name not in valid_attr_name:
        echo('mid3v2 attribute name was "{}" must be one of '.format(attr_name) + \
            ', '.join(x for x in valid_attr_name), abort=True)
    if quiet:
        out = syscmd('mid3v2 --{}="{}" "{}"'.format(attr_name, attr_value, fpath))
    else:
        syscmd('mid3v2 --{}="{}" "{}"'.format(attr_name, attr_value, fpath))
    return None

