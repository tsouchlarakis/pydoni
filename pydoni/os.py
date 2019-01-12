def listfiles(path='.', pattern=None, full_names=False, recursive=False, ignore_case=True, include_hidden_files=False):
    import os, sys
    if not os.path.isdir(path):
        print("ERROR: Invalid 'path' argument")
        sys.exit()
    wd = os.getcwd()
    os.chdir(path)
    fnames = [os.path.join(dp, f).replace('./', '')        \
        for dp, dn, filenames in os.walk('.')              \
        for f in filenames] if recursive else os.listdir()
    if not include_hidden_files:
        fnames = [fname for fname in fnames if not os.path.basename(fname).startswith('.')]
    if pattern:
        import re
        if ignore_case:
            fnames = [x for x in fnames if re.search(pattern, x, re.IGNORECASE)]
        else:
            fnames = [x for x in fnames if re.search(pattern, x)]
    if full_names:
        path_expand = os.getcwd() if path == '.' else path
        fnames = [os.path.join(path_expand, fname) for fname in fnames]
    os.chdir(wd)
    return sorted(fnames)

def listdirs(path='.', full_names=False):
    # List subdirectories
    import os
    wd = os.getcwd()
    os.chdir(path)
    dnames = next(os.walk(path))[1]
    if full_names:
        path_expand = os.getcwd() if path == '.' else path
        dnames = [os.path.join(path_expand, dname) for dname in dnames]
    os.chdir(wd)
    return sorted(dnames)

def getFinderComment(filepath):
    import os
    cmd = 'mdls -r -nullMarker "" -n kMDItemFinderComment "%s"' % filepath
    return os.popen(cmd).read()

def writeFinderComment(filepath, comment):
    import re
    cmd = '/usr/bin/osascript -e'
    applescript = 'set filepath to POSIX file "%s"\nset the_file to filepath as alias\ntell application "Finder" to set the comment of the_file to "%s"' % (filepath, comment)
    applescript = re.sub(r'"', r'\"', applescript)
    syscmd(cmd + ' "' + applescript + '"')

def removeFinderComment(filepath):
    import os, re
    cmd = '/usr/bin/osascript -e'
    applescript = 'set filepath to POSIX file "%s"\nset the_file to filepath as alias\ntell application "Finder" to set the comment of the_file to ""' % filepath
    applescript = re.sub(r'"', r'\"', applescript)
    os.system(cmd + ' "' + applescript + '"')    

def getFinderTags(filepath):
    import os
    cmd = 'mdls -r -nullMarker "" -n kMDItemUserTags "%s"' % filepath
    tags = os.popen(cmd).read()
    tags = [x.strip() for x in tags.split('\n') if '(' not in x and ')' not in x]
    tags = [x.replace(',', '') for x in tags]
    return tags if isinstance(tags, list) and len(tags) > 1 else tags[0]

def writeFinderTags(filepath, tags):
    import os
    if isinstance(tags, list):
        for tag in tags:
            syscmd('tag --add "%s" "%s"' % (tag, filepath))
    elif isinstance(tags, str):
        syscmd('tag --add "%s" "%s"' % (tags, filepath))
    else:
        print("ERROR: 'tags' argument must be of type list or str")

def removeFinderTags(filepath, tags):
    import os
    if tags == 'all':
        tags_exist = GetFinderTag(filepath)
        for tag in tags_exist:
            syscmd('tag --remove "%s" "%s"' % (tag, filepath))
    else:
        if isinstance(tags, list):
            for tag in tags:
                syscmd('tag --remove "%s" "%s"' % (tag, filepath))
        elif isinstance(tags, str):
            syscmd('tag --remove "%s" "%s"' % (tags, filepath))
        else:
            print("ERROR: 'tags' argument must be of type list or str")

def checkDpath(dpaths=[]):
    import os
    from PyFunctions import echo, clickfmt
    if not isinstance(dpaths, list):
        dpaths = [dpaths]
    for dpath in dpaths:
        if not os.path.isdir(dpath):
            echo('Directory {} does not exist'.format(clickfmt(dpath, 'filepath')), abort=True)

def fmtSeconds(time_in_sec, units='auto', round_digits=4):  # Format time in seconds
    from PyFunctions import echoError
    if units == 'auto':
        if time_in_sec < 60:
            time_diff = round(time_in_sec, round_digits)
            time_measure = 'seconds'
        elif time_in_sec >= 60 and time_in_sec < 3600:
            time_diff = round(time_in_sec/60, round_digits)
            time_measure = 'minutes'
        elif time_in_sec >= 3600 and time_in_sec < 86400:
            time_diff = round(time_in_sec/3600, round_digits)
            time_measure = 'hours'
        else:
            time_diff = round(time_in_sec/86400, round_digits)
            time_measure = 'days'
    elif units in ['seconds', 'minutes', 'hours', 'days']:
        time_measure = units
        if units == 'seconds':
            time_diff = round(time_in_sec, round_digits)
        elif units == 'minutes':
            time_diff = round(time_in_sec/60, round_digits)
        elif units == 'minutes':
            time_diff = round(time_in_sec/3600, round_digits)
        else:  # Days
            time_diff = round(time_in_sec/86400, round_digits)
    else:
        echoError("Invalid 'units' parameter. Must be one of 'auto', 'seconds', 'minutes', 'hours' or 'days'")
        return None
    return dict(zip(['units', 'value'], [time_measure, time_diff]))