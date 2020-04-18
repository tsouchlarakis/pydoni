import pydoni


class EXIF(object):
    """
    Extract and operate on EXIF metadata from a media file or multiple files. Wrapper for
    `exiftool` by Phil Harvey system command.

    :param fname: full path to target filename or list of filenames
    :type fname: str, list
    """

    def __init__(self, fpath):

        import os
        import subprocess
        import pydoni
        import pydoni.sh

        self.fpath = pydoni.ensurelist(fpath)
        self.fpath = [os.path.abspath(f) for f in self.fpath]
        for f in self.fpath:
            assert os.path.isfile(f)

        self.is_batch = len(self.fpath) > 1
        self.bin = pydoni.sh.find_binary('exiftool')

        assert os.path.isfile(self.bin)

        self.logger = pydoni.logger_setup(
            name=pydoni.what_is_my_name(classname=self.__class__.__name__, with_modname=True),
            level=pydoni.modloglev)

        self.logger.var('self.fpath', self.fpath)
        self.logger.var('self.is_batch', self.is_batch)
        self.logger.var('self.bin', self.bin)

        self.logger.info('EXIF class initialized for file{}: {}'.format(
            's' if self.is_batch else '', str(self.fpath)))

    def extract(self, method='doni', clean=True):
        """
        Extract EXIF metadata from file or files.

        :param method: method for metadata extraction, one of 'doni' or 'pyexiftool'
        :type method: str
        :param clean: apply EXIF.clean() to EXIF output
        :type clean: bool
        :return: EXIF metadata
        :rtype: dict
        """

        import re
        import os
        from xml.etree import ElementTree
        from collections import defaultdict
        import subprocess

        assert method in ['doni', 'pyexiftool']

        self.logger.var('self.method', method)
        self.logger.var('self.clean', clean)

        def split_cl_filenames(files, char_limit, bin_path):
            """
            Determine at which point to split list of filenames to comply with command-line
            character limit, and split list of filenames into list of lists, where each sublist
            represents a batch of files to run `exiftool` on, where the entire call to `exiftool`
            for that batch will be under the maximum command-line character limit. Files must
            be broken into batches if there are too many to fit on in command-line command,
            because the `exiftool` syntax is as follows:

            exiftool filename_1 filename_2 filename_3 ... filename_n

            With too many files, the raw length of the call to `exiftool` might be over the
            character limit.

            :param files: path to file or files to run exiftool on
            :type files: list
            :param char_limit: character limit of operating system's command-line character limit
            :type char_limit: int
            :param bin_path: path to exiftool binary
            :type bin_path: str
            :return: list of filenames to run exiftool on
            :rtype: list
            """

            self.logger.var('files', files)
            self.logger.var('char_limit', char_limit)
            self.logger.var('bin_path', bin_path)

            split_idx = []
            count = 0

            # Get character length of each filename
            str_lengths = [len(x) for x in files]

            # Get indices to split at depending on character limit
            for i in range(len(str_lengths)):
                # Account for two double quotes and a space
                val = str_lengths[i] + 3
                count = count + val
                if count > char_limit - len(bin_path + ' '):
                    split_idx.append(i)
                    count = 0

            # Split list of filenames into list of lists at the indices gotten in
            # the previous step
            return pydoni.split_at(files, split_idx)

        def etree_to_dict(t):
            """
            Convert XML ElementTree to dictionary.

            Source: https://stackoverflow.com/questions/7684333/converting-xml-to-dictionary-using-elementtree

            :param t: XML ElementTree
            :type t: ElementTree
            :return: dictionary
            :rtype: dict
            """

            self.logger.var('t', t)

            d = {t.tag: {} if t.attrib else None}
            children = list(t)

            if children:
                dd = defaultdict(list)
                for dc in map(etree_to_dict, children):
                    for k, v in dc.items():
                        dd[k].append(v)
                d = {t.tag: {k: v[0] if len(v) == 1 else v
                             for k, v in dd.items()}}

            if t.attrib:
                d[t.tag].update(('@' + k, v)
                                for k, v in t.attrib.items())

            if t.text:
                text = t.text.strip()
                if children or t.attrib:
                    if text:
                      d[t.tag]['#text'] = text
                else:
                    d[t.tag] = text

            return d

        def unnest_http_keynames(d):
            """
            Iterate over dictionary and test for key:value pairs where `value` is a
            dictionary with a key name in format "{http://...}". Iterate down until the
            terminal value is retrieved, then return that value to the original key name `key`

            :param d: dictionary to iterate over
            :type d: dict
            :returns: dictionary with simplified key:value pairs
            :rtype: dict
            """
            self.logger.var('d', d)

            tmpd = {}

            for k, v in d.items():

                while isinstance(v, dict) and len(v) == 1:
                    key = list(v.keys())[0]
                    if re.search(r'\{http:\/\/.*\}', key):
                        v = v[key]
                    else:
                        break

                tmpd[k] = v

            return tmpd


        self.logger.info("Running with method: " + method)

        if method == 'doni':

            num_files = len(self.fpath) if self.is_batch else 1
            self.logger.info("Extracting EXIF for files: " + str(num_files))

            self.logger.info("Exiftool binary found: " + self.bin)

            char_limit = int(pydoni.syscmd("getconf ARG_MAX")) - 25000
            self.logger.info("Using char limit: " + str(char_limit))

            file_batches = split_cl_filenames(self.fpath, char_limit, self.bin)
            self.logger.info("Batches to run: " + str(len(file_batches)))

            commands = []
            for batch in file_batches:
                cmd = self.bin + ' -xmlFormat ' + ' '.join(['"' + f + '"' for f in batch]) + ' ' + '2>/dev/null'
                commands.append(cmd)

            exifd = {}


            for i, cmd in enumerate(commands):

                self.logger.info("Running batch %s of %s. Total files: %s" % \
                    (str(i+1), str(len(file_batches)), str(len(file_batches[i]))))

                try:
                    # xmlstring = pydoni.syscmd(cmd).decode('utf-8')
                    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
                    xmlstring, err = proc.communicate()
                    xmlstring = xmlstring.decode('utf-8')
                except Exception as e:
                    self.logger.exception("Failed in executing `exiftool` system command")
                    raise e

                try:
                    root = ElementTree.fromstring(xmlstring)
                    elist = etree_to_dict(root)
                    elist = elist['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF']
                    elist = elist['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description']
                    if isinstance(elist, dict):
                        elist = [elist]

                except Exception as e:
                    self.logger.info("Failed in coercing ElementTree to dictionary")
                    raise e

                for d in elist:
                    tmpd = {}

                    # Clean dictionary keys in format @{http://...}KeyName
                    for k, v in d.items():
                        new_key = re.sub(r'@?\{.*\}', '', k)
                        tmpd[new_key] = v

                    # Unnest nested dictionary elements with "http://..." as the keys
                    tmpd = unnest_http_keynames(tmpd)

                    fnamekey = os.path.join(tmpd['Directory'], tmpd['FileName'])
                    exifd[fnamekey] = tmpd

                del elist

            self.logger.info("Successfully extracted EXIF metadata for named file(s)")

            if clean:
                return self.clean(exifd)
            else:
                return exifd

        elif method == 'pyexiftool':

            import exiftool

            with exiftool.ExifTool() as et:

                if self.is_batch:
                    exifd = et.get_metadata_batch(self.fpath)
                else:
                    exifd = et.get_metadata(self.fpath)

            return exifd

    def write(self, tags, values):
        """
        Write EXIF attribute(s) on a file or list of files.

        :param tags: tag names to write to
        :type tags: str, list
        :param values: desired tag values
        :type values: str, list
        :return: True
        :rtype: bool
        """

        import pydoni
        import pydoni.sh

        self.logger.var('tags', tags)
        self.logger.var('values', values)

        tags = [tags] if isinstance(tags, str) else tags
        values = [values] if isinstance(values, str) or isinstance(values, int) else values
        assert len(tags) == len(values)

        self._is_valid_tag_name(tags)

        self.logger.info("Files to write EXIF metadata to: " + str(len(files)))
        self.logger.info("Tags to write: " + str(tags))
        self.logger.info("Values to write: " + str(values))

        for file in files:
            self.logger.info("File: " + file)

            for tag, value in zip(tags, values):

                default_cmd = '{} -overwrite_original -{}="{}" "{}"'.format(
                    self.bin, tag, str(value), file)

                if tag == 'Keywords':
                    # Must be written in format:
                    # exiftool -keywords=one -keywords=two -keywords=three FILE
                    # Otherwise, comma-separated keywords will be written as a single string
                    if isinstance(value, str):
                        if ',' in value:
                            value = value.split(', ')

                    if isinstance(value, list):
                        if len(value) > 1:
                            kwd_cmd = ' '.join(['-keywords="' + str(x) + '"' for x in value])

                    if 'kwd_cmd' in locals():
                        cmd = '{} -overwrite_original {} "{}"'.format(
                            self.bin, kwd_cmd, file)
                    else:
                        cmd = default_cmd

                else:
                    cmd = default_cmd

                try:
                    self.logger.var('cmd', cmd)
                    res = pydoni.syscmd(cmd, encoding='utf-8')
                    self.logger.var('res', res)

                    if self._is_valid_tag_message(res):
                        self.logger.info("Success. Tag: %s | Value: %s" % (tag, str(value)))
                    else:
                        self.logger.info("Failed. Tag: %s | Value: %s" % (tag, str(value)))

                except Exception as e:
                    self.logger.exception("Failed. Tag: %s | Value: %s" % (tag, str(value)))
                    raise e

        return True

    def remove(self, tags):
        """
        Remove EXIF attribute from a file or list of files.

        :param tags: tag names to remove
        :type tags: str, list
        :return: True
        :rtype: bool
        """

        self.logger.var('tags', tags)

        tags = [tags] if isinstance(tags, str) else tags

        self._is_valid_tag_name(tags)

        self.logger.info("Files to remove EXIF metadata from: " + str(len(files)))
        self.logger.info("Tags to remove: " + str(tags))

        for file in files:
            self.logger.info("File: " + file)

            for tag in tags:
                cmd = '{} -overwrite_original -{}= "{}"'.format(self.bin, tag, file)

                try:
                    self.logger.var('cmd', cmd)
                    res = pydoni.syscmd(cmd, encoding='utf-8')
                    self.logger.var('res', res)

                    if self._is_valid_tag_message(res):
                        self.logger.info("Success. Tag: %s" % tag)
                    else:
                        self.logger.error("ExifTool Error. Tag: %s" % tag)
                        self.logger.debug('ExifTool output: %s' % str(res))

                except Exception as e:
                    self.logger.exception("Failed. Tag: %s" % tag)
                    raise e

    def clean(self, exifd):
        """
        Attempt to coerce EXIF values to Python data structures where possible. Try to coerce
        numerical values to Python int or float datatypes, dates to Python datetime values,
        and so on.

        Examples:
            '+7' -> 7
            '-7' -> -7
            '2018:02:29 01:28:10' -> '2018-02-29 01:28:10'
            '11.11' -> 11.11

        :param exifd: dictionary of extracted EXIF metadata
        :type exifd: dict
        :return: dictionary with cleaned values where possible
        :type: dict
        """

        self.logger.var('exifd', exifd)

        def detect_dtype(val):
            """
            Detect datatype of value.

            :param val: value to test
            :type val: any
            :return: one of ['bool', 'float', 'int', 'date', 'datetime', 'str']
            :rtype: str
            """

            self.logger.var('val', val)

            for dtype in ['bool', 'float', 'int', 'datetime', 'date', 'str']:
                if dtype == 'str':
                    return dtype
                else:
                    if pydoni.test(val, dtype):
                        return dtype

            return 'str'

        newexifd = {}
        for file, d in exifd.items():
            newexifd[file] = {}

            for k, v in d.items():
                dtype = detect_dtype(v)
                if dtype in ['bool', 'date', 'datetime', 'int', 'float']:
                    coerced_value = pydoni.test(v, dtype, return_coerced_value=True)
                    if v != coerced_value:
                        newexifd[file][k] = coerced_value
                        continue

                newexifd[file][k] = v

        return newexifd

    def _is_valid_tag_name(self, tags):
        """
        Check EXIF tag names for illegal characters.

        :param tags: list of tag names to validate
        :type tags: list
        :return: True
        :rtype: bool
        """
        self.logger.var('tags', tags)

        illegal_chars = ['-', '_']
        for tag in tags:
            for char in illegal_chars:
                if char in tag:
                    self.logger.error("Illegal char '%s' in tag name '%s'" % (char, tag))
                    assert char not in tag

        return True

    def _is_valid_tag_message(self, tagmsg):
        """
        Determine if EXIF write was successful based on tag message.

        :param tagmsg: output tag message
        :type tagmsg: str
        :return: True if successful, False otherwise
        :rtype: bool
        """
        self.logger.var('tagmsg', tagmsg)

        if 'nothing to do' in tagmsg.lower():
            return False
        else:
            return True


class FFmpeg(object):
    """
    Wrapper for FFmpeg BASH commands.
    """

    def __init__(self):
    
        import os
        import pydoni
        import pydoni.sh

        self.bin = pydoni.sh.find_binary('ffmpeg')
        assert os.path.isfile(self.bin)

        self.logger = pydoni.logger_setup(
            name=pydoni.what_is_my_name(classname=self.__class__.__name__, with_modname=True),
            level=pydoni.modloglev)

        self.logger.logvars(locals())

    def compress(self, file, outfile=None):
        """
        Compress audiofile on system by exporting it at 32K.

        :param file: paths to file or files to compress
        :type file: str, list
        :param outfile: paths to file or files to write to. If specified, must be same length
                        as `file`. If None (default), outfile name will be generated for each file.
        :type outfile: str, list or None
        """

        import os

        self.logger.logvars(locals())

        files = pydoni.ensurelist(file)
        for f in files:
            if not os.path.isfile(f):
                self.logger.error("File does not exist: " + f)
                assert os.path.isfile(f)

        if outfile is not None:
            outfiles = pydoni.ensurelist(outfile)
            if len(files) != len(outfiles):
                self.logger.error("Specified input and output filepaths are of different lengths")
                assert len(files) == len(outfiles)

        for i, f in enumerate(files):
            tmpoutfile = pydoni.append_filename_suffix(f, '-COMPRESSED') if outfile is None else outfiles[i]
            if os.path.isfile(tmpoutfile):
                os.remove(tmpoutfile)

            try:
                cmd = '{} -i "{}" -map 0:a:0 -b:a 32k "{}"'.format(self.bin, f, tmpoutfile)
                self.logger.debug(cmd)

                pydoni.syscmd(cmd)
                self.logger.info("Compressed '%s' to '%s'" % (f, tmpoutfile))

            except Exception as e:
                if os.path.isfile(tmpoutfile):
                    os.remove(tmpoutfile)

                self.logger.exception('Failed to run FFMpeg to compress audiofile')
                raise e

    def join(self, audiofiles, outfile):
        """
        Join multiple audio files into a single audio file using a direct call to FFMpeg.

        :param audiofiles: list of audio filenames to join together
        :type audiofiles: list
        :param outfile: name of file to create from joined audio files
        :type outfile: str
        """

        import os

        self.logger.logvars(locals())

        assert isinstance(audiofiles, list)
        assert len(audiofiles) > 1

        fname_map = {}
        replace_strings = {
            "'": 'SINGLEQUOTE'
        }
        self.logger.var('replace_strings', replace_strings)

        audiofiles = [os.path.abspath(f) for f in audiofiles]
        self.logger.var('audiofiles', audiofiles)

        tmpfile = os.path.join(
            os.path.dirname(audiofiles[0]),
            '.tmp.pydoni.audio.FFmpeg.join.%s.txt' % pydoni.systime(stripchars=True))
        self.logger.var('tmpfile', tmpfile)

        with open(tmpfile, 'w') as f:
            for fname in audiofiles:
                newfname = fname
                for key, val in replace_strings.items():
                    newfname = newfname.replace(key, val)

                fname_map[fname] = newfname
                os.rename(fname, newfname)
                f.write("file '%s'\n" % newfname)

        self.logger.var('fname_map', fname_map)
        # Old command 2020-01-30 15:59:04
        # cmd = 'ffmpeg -i "concat:{}" -acodec copy "{}"'.format('|'.join(audiofiles), outfile)

        cmd = '{} -f concat -safe 0 -i "{}" -c copy "{}"'.format(self.bin, tmpfile, outfile)
        self.logger.var('cmd', cmd)
        pydoni.syscmd(cmd)

        for f, nf in fname_map.items():
            os.rename(nf, f)

        if os.path.isfile(tmpfile):
            os.remove(tmpfile)

    def split(self, audiofile, segment_time):
        """
        Split audiofile into `segment_time` second size chunks.

        :param audiofile: audiofile to split
        :type audiofile: str
        :param segment_time: desired number of seconds of each chunk
        :type segment_time: int
        """

        import os

        audiofile = os.path.abspath(audiofile)
        cmd = '{} -i "{}" -f segment -segment_time {} -c copy "{}-ffmpeg-%03d{}"'.format(
            self.bin,
            audiofile,
            segment_time,
            os.path.splitext(audiofile)[0],
            os.path.splitext(audiofile)[1])

        self.logger.logvars(locals())

        pydoni.syscmd(cmd)

    def m4a_to_mp3(self, m4a_file):
        """
        Use ffmpeg to convert a .m4a file to .mp3.

        :param m4a_file: path to file to convert to .mp3
        :type m4a_file: str
        """
        import os
        
        m4a_file = os.path.abspath(m4a_file)
        cmd = '{} -i "{}" -codec:v copy -codec:a libmp3lame -q:a 2 "{}.mp3"'.format(
            self.bin, m4a_file, os.path.splitext(m4a_file)[0])

        self.logger.logvars(locals())

        pydoni.syscmd(cmd)

    def to_gif(self, moviefile, giffile=None, fps=10):
        """
        Convert movie file to gif.

        :param moviefile: path to movie file
        :type moviefile: str
        :param giffile: path to output gif file. If None, then use same name as `moviefile`
                        but substitute extension for '.gif'
        :type giffile: str, None
        :param fps: desired frames per second of output gif
        :type fps: int
        """
        import os

        outfile = giffile if giffile is not None else os.path.splitext(moviefile)[0] + '.gif'
        moviefile = os.path.abspath(moviefile)
        cmd = '{} -i "{}" -r {} "{}"'.format(self.bin, moviefile, str(fps), outfile)

        if os.path.isfile(outfile):
            os.remove(outfile)

        self.logger.logvars(locals())
        pydoni.syscmd(cmd)


class Git(object):
    """
    House git command line function python wrappers.
    """
    import os

    def __init__(self):
        self.logger = pydoni.logger_setup(
            name=pydoni.what_is_my_name(classname=self.__class__.__name__, with_modname=True),
            level=pydoni.modloglev)

    def is_git_repo(self, dir=os.getcwd()):
        """
        Determine whether current dir is a git repository.

        :param dir: directory to check if git repo
        :type dir: str
        :return: True if '.git' found in directory contents, False otherwise
        :rtype: bool
        """
        import os

        self.logger.logvars(locals())

        owd = os.getcwd()
        if dir != owd:
            os.chdir(dir)

        is_repo = True if '.git' in os.listdir() else False
        self.logger.info("'%s' is%s a git repo" % (dir, '' if is_repo else ' not'))

        if dir != owd:
            os.chdir(owd)

        return is_repo

    def status(self, dir=os.getcwd()):
        """
        Return boolean based on output of 'git status' command. Return True if working tree is
        up to date and does not require commit, False if commit is required.

        :return: bool
        """

        import os

        owd = os.getcwd()
        if dir != owd:
            os.chdir(dir)

        self.logger.logvars(locals())

        out = pydoni.syscmd('git status').decode()
        working_tree_clean = "On branch masterYour branch is up to date with 'origin/master'.nothing to commit, working tree clean"
        not_git_repo = 'fatal: not a git repository (or any of the parent directories): .git'

        if dir != owd:
            os.chdir(owd)

        if out.replace('\n', '') == working_tree_clean:
            self.logger.info('Status: Working tree clean')
            return True
        elif out.replace('\n', '') == not_git_repo:
            self.logger.info('Status: Not git repo')
            return None
        else:
            self.logger.info('Status: Commit required')
            return False

    def add(self, fpath=None, all=False):
        """
        Add files to commit.

        :param fpath: file(s) to add
        :type fpath: str, list
        :param all: execute 'git add .'
        :type all: bool
        """
        self.logger.var('fpath', fpath)
        self.logger.var('all', all)

        if all == True and fpath is None:
            pydoni.syscmd('git add .;', encoding='utf-8')
        elif isinstance(fpath, str):
            pydoni.syscmd('git add "%s";' % fpath, encoding='utf-8')
        elif isinstance(fpath, list):
            for f in fpath:
                pydoni.syscmd('git add "%s";' % f, encoding='utf-8')
        else:
            self.logger.error('Nonsensical `fpath` and `all` options! Nothing done.')

    def commit(self, msg):
        """
        Execute 'git commit -m {}' where {} is commit message.

        :param msg: commit message
        :type msg: str
        """
        self.logger.var('msg', msg)
        cmd = "git commit -m '{}';".format(msg)
        self.logger.var('cmd', cmd)
        subprocess.call(cmd, shell=True)

    def push(self):
        """
        Execute 'git push'.
        """
        cmd = "git push;"
        self.logger.var('cmd', cmd)
        subprocess.call(cmd, shell=True)

    def pull(self):
        """
        Execute 'git pull'.
        """
        cmd = "git pull;"
        self.logger.var('cmd', cmd)
        subprocess.call(cmd, shell=True)


class AppleScript(object):
    """
    Store Applescript-wrapper operations.
    """

    def __init__(self):
        self.logger = pydoni.logger_setup(
            name=pydoni.what_is_my_name(classname=self.__class__.__name__, with_modname=True),
            level=pydoni.modloglev)
        self.logger.logvars(locals())

    def execute(self, applescript):
        """
        Wrapper for pydoni.sh.osascript

        :param applescript:: applescript string to execute
        :type applescript: str
        """
        
        out = osascript(applescript)
        self.logger.logvars(locals())
        if 'error' in out.lower():
            raise Exception(str(out))

    def new_terminal_tab(self):
        """
        Make new Terminal window.
        """

        applescript = """
        tell application "Terminal"
            activate
            tell application "System Events" to keystroke "t" using command down
            repeat while contents of selected tab of window 1 starts with linefeed
                delay 0.01
            end repeat
        end tell"""

        self.logger.logvars(locals())
        self.execute(applescript)

    def execute_shell_script_in_new_tab(self, shell_script):
        """
        Create a new Terminal tab, then execute given shell scripts.

        :param shell_script: shell script string to execute in default shell
        :type shell_script: str
        """

        applescript = """
        tell application "Terminal"
            activate
            tell application "System Events" to keystroke "t" using command down
            repeat while contents of selected tab of window 1 starts with linefeed
                delay 0.01
            end repeat
            do script "{}" in window 1
        end tell
        """.format(shell_script.replace('"', '\\"'))
        applescript = applescript.replace('\\\\"', '\"')

        self.logger.logvars(locals())

        self.execute(applescript)


def find_binary(bin_name, bin_paths=['/usr/bin', '/usr/local/bin'], abort=False, return_first=False):
    """
    Find system binary by name. If multiple binaries found, return a list of binaries unless
    `return_first` is True, in which case just return the first binary found.

    Ex: find_binary('exiftool') will yield '/usr/local/exiftool' if exiftool installed, and
        it will return None if it's not installed

    :param bin_name: name of binary to search for
    :type bin_name: str
    :param bin_paths: list of paths to search for binary in
    :type bin_paths: list
    :param abort: raise FileNotFoundError if no binary found
    :type abort: bool
    :param return_first: if multiple matches found, return first found binary as string
    :type return_first: str
    :return: absolute path of found binary, else None
    :rtype: str or list if multiple matches found and `return_first` is False
    """

    import os

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    assert isinstance(bin_name, str)
    assert isinstance(bin_paths, list)

    owd = os.getcwd()
    logger.var('owd', owd)

    match = []
    for path in bin_paths:
        os.chdir(path)
        binaries = pydoni.listfiles()
        for binary in binaries:
            if bin_name == binary:
                match_item = os.path.join(path, binary)
                match.append(match_item)
                logger.info("Matching binary found %s" % match_item)

    if len(match) > 1:
        if return_first:
            logger.warn("Multiple matches found for `{}`, returning first: {}".format(bin_name, str(match)))
            return match[0]
        else:
            logger.warn("Multiple matches found for `{}`: {}".format(bin_name, str(match)))
            return match

    elif len(match) == 0:
        if abort:
            raise FileNotFoundError("No binaries found for: " + bin_name)
        else:
            logger.warn("No binaries found! Returning None.")
        return None

    os.chdir(owd)
    return match[0]


def adobe_dng_converter(fpath, overwrite=False):
    """
    Run Adobe DNG Converter on a file.

    :param fpath: path to file or files to run Adobe DNG Converter on
    :type fpath: str, list
    :param overwrite: if output file already exists, overwrite it
    :type overwrite: bool
    """

    import os

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)

    # Check if destination file already exists
    # Build output file with .dng extension and check if it exists
    fpath = pydoni.ensurelist(fpath)
    destfile = os.path.join(os.path.splitext(fpath)[0], '.dng')
    exists = True if os.path.isfile(destfile) else False

    logger.logvars(locals())

    # Build system command
    app = os.path.join('/', 'Applications', 'Adobe DNG Converter.app',
        'Contents', 'MacOS', 'Adobe DNG Converter')
    cmd = '"{}" "{}"'.format(app, fpath)

    logger.var('app', app)
    logger.var('cmd', cmd)

    # Execute command if output file does not exist, or if `overwrite` is True
    if exists:
        if overwrite:
            pydoni.syscmd(cmd)
        else:
            # File exists but `overwrite` not specified as True
            pass
    else:
        pydoni.syscmd(cmd)


def stat(fname):
    """
    Call 'stat' UNIX command and parse output into a Python dictionary.

    :param fname: path to file
    :type fname: str
    :returns: dictionary with items:
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
    :rtype: dict
    """

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    def parse_datestring(fname, datestring):
        """
        Extract datestring from `stat` output.

        fname: filename in question
        :type fname: str
            datestring: string containing date
            :type datestring: str
        """

        import os

        self.logger.logvars(locals())

        try:
            dt = datetime.datetime.strptime(datestring, '%a %b %d %H:%M:%S %Y')
            logger.var('dt', dt)
            return dt.strftime('%Y-%m-%d %H:%M:%S')

        except Exception as e:
            echo("Unable to parse date string {} for {} (original date string returned)". \
                format(clickfmt(datestring, 'date'), clickfmt(fname, 'filename')),
                warn=True, error_msg=str(e))
            return datestring

    assert os.path.isfile(fname)

    # Get output of `stat` command and clean for python list
    cmd = 'stat -x "{}"'.format(fname)
    res = pydoni.syscmd(cmd, encoding='utf-8')
    res = [x.strip() for x in res.split('\n')]

    logger.var('cmd', cmd)
    logger.var('res', res)

    # Tease out each element of `stat` output
    items = ['File', 'Size', 'FileType', 'Mode', 'Uid', 'Device', 'Inode', 'Links',
        'AccessDate', 'ModifyDate', 'ChangeDate']
    logger.var('items', items)

    out = {}
    for item in items:
        try:
            if item == 'File':
                out[item] = res[0].split(':')[1].split('"')[1]
            elif item == 'Size':
                out[item] = res[1].split(':')[1].strip().split(' ')[0]
            elif item == 'FileType':
                out[item] = res[1].split(':')[1].strip().split(' ')[1]
            elif item == 'Mode':
                out[item] = res[2].split(':')[1].strip().split(' ')[0]
            elif item == 'Uid':
                out[item] = res[2].split(':')[2].replace('Gid', '').strip()
            elif item == 'Device':
                out[item] = res[3].split(':')[1].replace('Inode', '').strip()
            elif item == 'Inode':
                out[item] = res[3].split(':')[2].replace('Links', '').strip()
            elif item == 'Links':
                out[item] = res[3].split(':')[3].strip()
            elif item == 'AccessDate' :
                out[item] = parse_datestring(fname, res[4].replace('Access:', '').strip())
            elif item == 'ModifyDate' :
                out[item] = parse_datestring(fname, res[5].replace('Modify:', '').strip())
            elif item == 'ChangeDate' :
                out[item] = parse_datestring(fname, res[6].replace('Change:', '').strip())

        except Exception as e:
            out[item] = '<pydoni.sh.stat() ERROR: %s>' % str(e)
            self.logger.exception("Error extracting key '%s' from stat output. Error message:" % item)
            self.logger.debug(str(e))

    return out


def mid3v2(fpath, attr_name, attr_value):
    """
    Use mid3v2 to add or overwrite a metadata attribute to a file.

    :param fpath: path to file
    :type fpath: str
    :param attr_name: name of attribute to assign value to using mid3v2, one of
                      ['artist', 'album', 'song', 'comment', 'picture', 'genre',
                      'year', 'date', 'track']
    :type attr_name: str
    :param attr_value: value to assign to attribute `attr_name`
    :type attr_value: str, int
    :return: boolean indicator of successful run
    :rtype: bool
    """

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    valid = ['artist', 'album', 'song', 'comment', 'picture', 'genre', 'year', 'date', 'track']
    logger.var('valid', valid)
    assert attr_name in valid

    bin = pydoni.sh.find_binary('mid3v2')
    logger.var('bin', bin)

    cmd = '{} --{}="{}" "{}"'.format(bin, attr_name, attr_value, fpath)
    logger.var('cmd', cmd)
    pydoni.syscmd(cmd)


def convert_audible(fpath, fmt, activation_bytes):
    """
    Convert Audible .aax file to .mp4.

    :param fpath: path to .aax file
    :type fpath: str
    :param fmt: one of 'mp3' or 'mp4', if 'mp4' then convert output file to mp3
    :type fmt: str
    :param activation_bytes: activation bytes string.
                             See https://github.com/inAudible-NG/audible-activator to get
                             activation byte string
    :type activation_bytes: str
    """

    import os

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    assert os.path.isfile(fpath)
    assert os.path.splitext(fpath)[1].lower() == '.aax'

    # Get output format
    fmt = fmt.lower().replace('.', '')
    assert fmt in ['mp3', 'mp4']

    # Get outfile
    outfile = os.path.splitext(fpath)[0] + '.mp4'
    logger.var('outfile', outfile)
    assert not os.path.isfile(outfile)

    # player_id = '2jmj7l5rSw0yVb/vlWAYkK/YBwk='
    # activation_bytes = '8a87c903'

    # Convert to mp4 (regardless of `fmt` parameter)
    bin = pydoni.sh.find_binary('ffmpeg')
    cmd = '{} -activation_bytes {} -i "{}" -vn -c:a copy "{}"'.format(
        bin, activation_bytes, fpath, outfile)
    logger.var('cmd', cmd)
    pydoni.syscmd(cmd)

    # Convert to mp3 if specified
    if fmt == 'mp3':
        self.logger.info('Converting MP4 to MP3 at 256k: ' + outfile)
        mp4_to_mp3(outfile, bitrate=256)


def mp4_to_mp3(fpath, bitrate):
    """
    Convert an .mp4 file to a .mp3 file.

    :param fpath: path to .mp4 file
    :type fpath: str
    :param bitrate: bitrate to export as, may also be as string for example '192k'
    :type bitrate: int
    """

    import os

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    assert os.path.splitext(fpath)[1].lower() == '.mp4'

    # Get bitrate as string ###k where ### is any number
    bitrate = str(bitrate).replace('k', '') + 'k'
    logger.var('bitrate', bitrate)
    assert re.match(r'\d+k', bitrate)

    # Execute command
    cmd = 'f="{}";ffmpeg -i "$f" -acodec libmp3lame -ab {} "${{f%.mp4}}.mp3";'.format(fpath, bitrate)
    logger.var('cmd', cmd)
    pydoni.syscmd(cmd)


def split_video_scenes(vfpath, outdname):
    """
    Split video using PySceneDetect.

    :param vfpath: path to video file to split
    :type vfpath: str
    :param outdname: path to directory to output clips to
    :type outdname: str
    :return: True if run successfully, False if run unsuccessfully
    :rtype: bool
    """

    import os

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    assert os.path.isfile(vfpath)
    assert os.isdir(outdname)

    cmd = 'scenedetect --input "{}" --output "{}" detect-content split-video'.format(vfpath, outdname)
    logger.var('cmd', cmd)

    try:
        pydoni.syscmd(cmd)
        return True
    except Exception as e:
        self.logger.exception('Failed to split video scenes')
        self.logger.debug(str(e))
        return False


def osascript(applescript):
    """
    Execute applescript.

    :param applescript: applescript string to execute
    :type applescript: str
    :return: output string from AppleScript command
    :rtype: str
    """

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)

    bin_name = pydoni.sh.find_binary('osascript')
    applescript = applescript.replace("'", "\'")

    cmd = "{bin_name} -e '{applescript}'".format(**locals())
    out = pydoni.syscmd(cmd)

    if isinstance(out, bytes):
        out = out.decode('utf-8')

    logger.logvars(locals())

    return out
