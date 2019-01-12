def syscmd(cmd, encoding=''):
    """
    Runs a command on the system, waits for the command to finish, and then
    returns the text output of the command. If the command produces no text
    output, the command's return code will be returned instead.
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

def exiftool(filepath, rmtags=None):
    import subprocess, re
    from PyFunctions import syscmd, echoError
    if rmtags:
        if isinstance(rmtags, str):
            res = syscmd('exiftool -overwrite_original -{}= "{}"'.format(rmtags, filepath))
        elif isinstance(rmtags, list):
            for tag in remove_tags:
                res = syscmd('exiftool -overwrite_original -{}= "{}"'.format(tag, filepath))
        else:
            echoError("Parameter 'rmtags' must be of type str or list", fn_name='exiftool')
        return None
    # Normal call to this function
    res = subprocess.run('exiftool "%s"' % filepath, stdout=subprocess.PIPE, shell=True)
    res = str(res.stdout.decode('utf-8', errors='backslashreplace'))
    exif = [x for x in res.split('\n') if x > '']
    keys = [re.sub(r'^(.*?)(:)(.*)$', r'\1', x).strip() for x in exif]
    vals = [re.sub(r'^(.*?)(:)(.*)$', r'\3', x).strip() for x in exif]
    return dict(zip(keys, vals))

def stat(fname):  # Call 'stat' UNIX command and parse output into a Python dictionary
    from PyFunctions import syscmd
    def parseDatestring(fname, datestring):
        import datetime
        try:
            dt = datetime.datetime.strptime(datestring, '%a %b %d %H:%M:%S %Y')
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            from PyFunctions import echo, clickfmt
            echo("Unable to parse date string {} for {} (original date string returned)". \
                    format(clickfmt(datestring, 'date'), clickfmt(fname, 'filename')), warn=True)
            return datestring
    cmd = 'stat -x "{}"'.format(fname)
    res = syscmd(cmd).decode('utf-8')
    res = [x.strip() for x in res.split('\n')]
    return dict(
        File     = res[0].split(':')[1].split('"')[1],
        Size     = res[1].split(':')[1].strip().split(' ')[0],
        FileType = res[1].split(':')[1].strip().split(' ')[1],
        Mode     = res[2].split(':')[1].strip().split(' ')[0],
        Uid      = res[2].split(':')[2].replace('Gid', '').strip(),
        Device   = res[3].split(':')[1].replace('Inode', '').strip(),
        Inode    = res[3].split(':')[2].replace('Links', '').strip(),
        Links    = res[3].split(':')[3].strip(),
        AccessDate = parseDatestring(fname, res[4].replace('Access:', '').strip()),
        ModifyDate = parseDatestring(fname, res[5].replace('Modify:', '').strip()),
        ChangeDate = parseDatestring(fname, res[6].replace('Change:', '').strip()))