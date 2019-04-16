def listfiles(path='.', pattern=None, ext=None, full_names=False, recursive=False, ignore_case=True, include_hidden_files=False):
    from os import getcwd, walk, listdir, getcwd, chdir
    from os.path import isdir, join, basename, splitext
    from pydoni.vb import echo
    if not isdir(path):
        echo("Path '{}' does not exist".format(path), fn_name='listfiles', error=True)
        return None
    wd = getcwd()
    chdir(path)
    fnames = [join(dp, f).replace('./', '') \
        for dp, dn, filenames in walk('.') \
        for f in filenames] if recursive else listdir()
    if not include_hidden_files:
        fnames = [fname for fname in fnames if not basename(fname).startswith('.')]
    if pattern:
        import re
        if ignore_case:
            fnames = [x for x in fnames if re.search(pattern, x, re.IGNORECASE)]
        else:
            fnames = [x for x in fnames if re.search(pattern, x)]
    if ext:
        ext = [ext] if isinstance(ext, str) else ext
        ext = [x.lower() for x in ext]
        ext = ['.' + x if not x.startswith('.') else x for x in ext]
        fnames = [x for x in fnames if splitext(x)[1].lower() in ext]
    if full_names:
        path_expand = getcwd() if path == '.' else path
        fnames = [join(path_expand, fname) for fname in fnames]
    chdir(wd)
    return sorted(fnames)

def listdirs(path='.', pattern=None, full_names=False, recursive=False):
    # List subdirectories
    import os
    wd = os.getcwd()
    os.chdir(path)
    if recursive:
        dnames = [os.path.join(root, subdir).replace('./', '') \
            for root, subdirs, filenames in os.walk('.') \
            for subdir in subdirs]
    else:
        dnames = next(os.walk(path))[1]
        dnames = sorted(dnames)
    if full_names:
        path_expand = os.getcwd() if path == '.' else path
        dnames = [os.path.join(path_expand, dname) for dname in dnames]
    if pattern is not None:
        import re
        dnames = [x for x in dnames if re.match(pattern, x)]
    os.chdir(wd)
    return dnames

def getFinderComment(filepath):
    import os
    cmd = 'mdls -r -nullMarker "" -n kMDItemFinderComment "%s"' % filepath
    res = os.popen(cmd).read()
    res = '' if 'could not find ' + os.path.basename(filepath) in res else res
    return res

def writeFinderComment(filepath, comment):
    import re
    from pydoni.sh import syscmd
    cmd = '/usr/bin/osascript -e'
    applescript = 'set filepath to POSIX file "{}"\nset the_file to filepath as alias\ntell application "Finder" to set the comment of the_file to "{}"'
    applescript_clear = applescript.format(filepath, 'test')
    applescript_set = applescript.format(filepath, comment)
    applescript_clear = re.sub(r'"', r'\"', applescript_clear)
    applescript_set = re.sub(r'"', r'\"', applescript_set)
    res = syscmd(cmd + ' "' + applescript_clear + '"')
    res = syscmd(cmd + ' "' + applescript_set + '"')

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
    tags = [tags] if isinstance(tags, str) else tags
    return tags

def writeFinderTags(filepath, tags):
    import os
    from pydoni.sh import syscmd
    if isinstance(tags, list):
        for tag in tags:
            syscmd('tag --add "%s" "%s"' % (tag, filepath))
    elif isinstance(tags, str):
        syscmd('tag --add "%s" "%s"' % (tags, filepath))
    else:
        print("ERROR: 'tags' argument must be of type list or str")

def removeFinderTags(filepath, tags):
    import os
    from pydoni.sh import syscmd
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
    from pydoni.vb import echo, clickfmt
    if not isinstance(dpaths, list):
        dpaths = [dpaths]
    for dpath in dpaths:
        if not os.path.isdir(dpath):
            echo('Directory {} does not exist'.format(clickfmt(dpath, 'filepath')), abort=True)

def unarchive(fpath, dest_dir):
    """Unzip a .zip archive"""
    import zipfile
    with zipfile.ZipFile(fpath, 'r') as zip_ref:
        zip_ref.extractall(dest_dir)