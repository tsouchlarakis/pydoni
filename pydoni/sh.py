import datetime
import exiftool
import numpy as np
import re
import subprocess
from collections import Counter, OrderedDict
from itertools import chain
from os import listdir
from os import remove
from os.path import basename
from os.path import isdir
from os.path import isfile
from os.path import join
from os.path import splitext
from os.path import dirname


def syscmd(cmd, encoding=''):
    """
    Runs a command on the system, waits for the command to finish, and then
    returns the text output of the command. If the command produces no text
    output, the command's return code will be returned instead.
    
    Arguments:
        cmd      {str} -- command string to execute
        encoding {str} -- [optional] name of decoding to decode output bytestring with
    
    Returns:
        {str} or {int} -- interned system output {str}, or returncode {int}
    """
    p = subprocess.Popen(
        cmd,
        shell     = True,
        stdin     = subprocess.PIPE,
        stdout    = subprocess.PIPE,
        stderr    = subprocess.STDOUT,
        close_fds = True
    )
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
    
    Arguments:
        fpath     {str}  -- path to file
        overwrite {bool} -- if True, if output file already exists, overwrite it. if False, skip
    
    Returns:
        nothing
    """
    
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
            pass
    else:
        syscmd(cmd)


def stat(fname):
    """
    Call 'stat' UNIX command and parse output into a Python dictionary.
    
    Arguments:
        fname {str} -- path to file
    
    Returns:
        {dict} -- with items:
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
    
    def parse_datestring(fname, datestring):
        """
        Extract datestring from `stat` output.

        Arguments:
            fname {str} -- filename in question
            datestring {str} -- string containing date
        """
        try:
            dt = datetime.datetime.strptime(datestring, '%a %b %d %H:%M:%S %Y')
            return dt.strftime('%Y-%m-%d %H:%M:%S')

        except Exception as e:
            echo("Unable to parse date string {} for {} (original date string returned)". \
                format(clickfmt(datestring, 'date'), clickfmt(fname, 'filename')),
                warn=True, error_msg=str(e))
            return datestring
    
    assert isfile(fname)

    # Get output of `stat` command and clean for python list
    cmd = 'stat -x "{}"'.format(fname)
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
    
    Arguments:
        fpath {str} -- path to file
        attr_name {str} -- name of attribute to assign value to using mid3v2, one of ['artist', 'album', 'song', 'comment', 'picture', 'genre', 'year', 'date', 'track']
        attr_value {str or int} -- value to assign to attribute `attr_name`
    
    Keyword Arguments:
        quiet {bool} -- if True, do not print any output to STDOUT (default: {True})
    
    Returns:
        {bool} -- if True, successfully run. If False, failed
    """

    # Check that attribute name is valid
    valid = ['artist', 'album', 'song', 'comment', 'picture', 'genre', 'year', 'date', 'track']
    assert attr_name in valid

    # Build command
    cmd = 'mid3v2 --{}="{}" "{}"'.format(attr_name, attr_value, fpath)

    # Execute command
    try:
        if quiet:
            out = syscmd(cmd)
            del out
        else:
            syscmd(cmd)
        return True
    except Exception as e:
        echo('failed', error=True, error_msg=str(e), fn_name='mid3v2')
        return False
    

def convert_audible(fpath, fmt, activation_bytes):
    """
    Convert Audible .aax file to .mp4.
    
    Arguments:
        fpath {str} -- path to .aax file
        fmt {str} -- one of 'mp3' or 'mp4'
        activation_bytes {str} -- activation bytes string. See https://github.com/inAudible-NG/audible-activator to get activation byte string
    
    Returns:
        nothing
    """
    assert isfile(fpath)
    assert splitext(fpath)[1].lower() == '.aax'

    # Get output format
    fmt = fmt.lower().replace('.', '')
    assert fmt in ['mp3', 'mp4']
    
    # Get outfile
    outfile = splitext(fpath)[0] + '.mp4'
    assert not isfile(outfile)
    
    # player_id = '2jmj7l5rSw0yVb/vlWAYkK/YBwk='
    # activation_bytes = '8a87c903'
    
    # Convert to mp4 (regardless of `fmt` parameter)
    cmd = 'ffmpeg -activation_bytes {} -i "{}" -vn -c:a copy "{}"'.format(
        activation_bytes,
        fpath,
        outfile
    )
    syscmd(cmd)

    # Convert to mp3 if specified
    if fmt == 'mp3':
        mp4_to_mp3(outfile, bitrate=256)


def mp4_to_mp3(fpath, bitrate):
    """
    Convert an .mp4 file to a .mp3 file.

    Arguments:
        fpath {str} -- path to .mp4 file
        bitrate {int} -- bitrate to export as, may also be as string for example '192k'

    Returns:
        nothing
    """
    assert splitext(fpath)[1].lower() == '.mp4'
    
    # Get bitrate as string ###k where ### is any number
    bitrate = str(bitrate).replace('k', '') + 'k'
    assert re.match(r'\d+k', bitrate)
    
    # Execute command
    cmd = 'f="{}";ffmpeg -i "$f" -acodec libmp3lame -ab {} "${{f%.mp4}}.mp3";'.format(fpath, bitrate)
    syscmd(cmd)


def split_video_scenes(vfpath, outdname):
    """
    Split video using PySceneDetect.
    
    Arguments:
        vfpath {str} -- path to video file to split
        outdname {str} -- path to directory to output clips to
    
    Returns:
        {bool} -- True if run successfully, False if run unsuccessfully
    """

    assert isfile(vfpath)
    assert isdir(outdname)

    # Build command
    cmd = 'scenedetect --input "{}" --output "{}" detect-content split-video'.format(
        vfpath, outdname)
    
    # Execute command
    try:
        syscmd(cmd)
        return True
    except:
        return False


class EXIF(object):
    """
    Extract and handle EXIF metadata from file.
    
    Arguments:
        fname {str} or {list} -- filename or list of filenames to initiate EXIF class on
    """

    def __init__(self, fname):
        assert isinstance(fname, list) or isinstance(fname, str)
        self.fname = fname
        if isinstance(self.fname, list):
            if len(self.fname) > 1:
                self.batch = True
            else:
                self.batch = False
        else:
            self.batch = False
        if self.batch:
            self.num_files = len(self.fname)
        else:
            self.num_files = 1

    def run(self, wrapper='doni', attr_name=None, dedup=True, verbose=False):
        """
        Run Exiftool using either Doni algorithm or PyExifTool package on either a single file
        or a batch of files.
        
        Arguments:
            wrapper {str} -- wrapper name of exiftool program to run, one of ['doni', 'pyexiftool']
            verbose {bool} -- if True, messages are printed to STDOUT
        
        Returns:
            {dict}
        """
        if wrapper == 'doni':
            self.exif = self.exiftool(
                attr_name=attr_name, dedup=dedup, verbose=verbose)
            return self.exif

        elif wrapper == 'pyexiftool':
            with exiftool.ExifTool() as et:
                if isinstance(self.fname, list):
                    self.exif = et.get_metadata_batch(self.fname)
                else:
                    self.exif = et.get_metadata(self.fname)
            return self.exif

    def exiftool(self, attr_name=None, dedup=True, verbose=False):
        """
        Run `exiftool` on a file and fetch output.
        
        Arguments:
            rmtags {str} or {list} -- name(s) of tags to remove with `exiftool`
            dedup {bool} -- if True, names of EXIF attributes will be checked for duplicate names. If any are found, a suffix is appended. Suffixes may be "_2", "_3", ...
            attr_name {str} or {list} -- filter output exif dictionary by attribute name(s)
        
        Returns:
            dict
        """

        def break_into_commandline_batches(fnames, char_limit):
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
            
            Arguments:
                fnames {str} or {list} -- path to file(s)
                char_limit {int} -- character limit of operating system's command-line character limit
            
            Returns:
                dictionary of lists
            """

            # Initialize process
            split_fname = []
            count = 0

            # Get character length of each filename
            str_lengths = [len(x) for x in self.fname]

            # Get indices to split at depending on character limit
            for i in range(len(str_lengths)):
                # Account for two double quotes and a space
                val = str_lengths[i] + 3
                count = count + val
                if count > char_limit - len('exiftool '):
                    split_fname.append(i)
                    count = 0

            # Split list of filenames into list of lists at the indices gotten in
            # the previous step
            fname_batches = split_at(self.fname, split_fname)

            # Convert list of lists to dictionary with 'batch_${i}' as each key name
            fname_batches_dict = OrderedDict()
            for i, lst in enumerate(fname_batches):
                fname_batches_dict['batch_' + str(i)] = lst

            return fname_batches_dict

        def parse_raw_exiftool_output(res, fnames, attr_name, dedup):
            """
            Parse raw exiftool output string, coerce to a dictionary.
            
            Arguments:
                res {str} -- raw exiftool output string
            
            Returns:
                {dict}
            """

            # Convert string result to list
            res = res.split('\n')

            # Get split locations in each result list. When you call `exiftool` with multiple
            # files, the result will be delimited by '========' for each file
            split_loc = [i for i, x in enumerate(
                res) if x.startswith('========')]
            for i in split_loc:  # Assign split locations to nan
                res[i] = np.nan
            # This will leave nan elements as own lists
            res = split_at(res, split_loc)

            # Clean result by removing empty strings where '========' used to be
            res = [x for x in res if len(x) > 0]
            res = [x[1:len(x)] for x in res]

            # Parse Exiftool output: extract keys, extract values, zip each into dictionary
            exifd = {}
            for i, exif_result in enumerate(res):
                # Extract keys and values
                keys = [re.sub(
                    r'^(.*?)(:)(.*)$', r'\1', x).strip().replace(' ', '_').lower() for x in exif_result]
                vals = [re.sub(r'^(.*?)(:)(.*)$', r'\3', x).strip()
                        for x in exif_result]

                # Remove final element if it's an empty string. This is a result of parsing the
                # exiftool output string in the previous step
                if keys[len(keys)-1] == '':
                    keys = keys[0:len(keys)-1]
                if vals[len(vals)-1] == '':
                    vals = vals[0:len(vals)-1]
                assert len(keys) == len(vals)

                # Filter result if specified
                if attr_name is not None:
                    attr_name = [attr_name] if isinstance(
                        attr_name, str) else attr_name
                    vals = [x for i, x in enumerate(
                        vals) if keys[i] in attr_name]
                    keys = [x for x in keys if x in attr_name]

                # Zip into dictionary and append to `exifd` master dictionary
                d = dict(zip(keys, vals))
                exifd[fnames[i]] = d

                # Mark any duplicate keys with a _\d suffix to ensure no duplicate keys
                if dedup:
                    for fname, d in exifd.items():
                        keys = [k for k, v in d.items()]
                        vals = [v for k, v in d.items()]
                        if any(duplicated(keys)):
                            # so we have: {'name':3, 'state':1, 'city':1, 'zip':2}
                            counts = Counter(keys)
                            for s, num in counts.items():
                                if num > 1:  # ignore strings that only appear once
                                    # suffix starts at 1 and increases by 1 each time
                                    for suffix in range(1, num + 1):
                                        # replace each appearance of s
                                        keys[keys.index(s)] = s + \
                                            '_' + str(suffix)
                        exifd[fname] = dict(zip(keys, vals))

            # If only run on one file, do not format dictionary with key as filename,
            # since there is only a single file. Simply return the exif metadata portion
            # of the resulting dictionary
            if len(exifd) == 1:
                return exifd[list(exifd.keys())[0]]
            else:
                return exifd

        # Check if `exiftool` is installed
        ep = syscmd('which /usr/local/bin/exiftool').decode().strip()
        if not isfile(ep):
            echo("exiftool is not installed! Please install it per instructions with `brew install exiftool`", abort=True)

        if verbose:
            echo('Number of files detected           : %s' %
                self.num_files, timestamp=True, fn_name='exiftool')
            est_time = fmt_seconds(0.06079523*len(self.fname), round_digits=0)
            echo('Expected program time              : %s %s' % (
                est_time['value'], est_time['units']), timestamp=True, fn_name='exiftool')

        char_limit = int(syscmd("getconf ARG_MAX")) - 25000
        if verbose:
            echo('Using command-line character limit : %s' % str(char_limit),
                timestamp=True, fn_name="EXIF.run(..., wrapper='doni')")

        # Cast filenames as list if not already
        if not isinstance(self.fname, list):
            self.fname = [self.fname]

        # Break files into batches based on command-line character limit
        fname_batches = dict(
            break_into_commandline_batches(self.fname, char_limit))

        if verbose:
            echo('Number of batches to run           : %s' % str(len(fname_batches)),
                timestamp=True, fn_name="EXIF.run(..., wrapper='doni')")
            echo('Running exiftool...', timestamp=True,
                fn_name="EXIF.run(..., wrapper='doni')")

        exifmaster = {}
        for batch_name, batch_files in fname_batches.items():
            # Iterate over batches and append results to master dictionary

            # Obtain exiftool result
            cmd = '/usr/local/bin/exiftool ' + \
                ' '.join('"' + item + '"' for item in batch_files)
            res = subprocess.run(cmd, stdout=subprocess.PIPE, shell=True)
            res = str(res.stdout.decode('utf-8', errors='backslashreplace'))

            # Parse exiftool output to dictionary
            exifd = parse_raw_exiftool_output(
                res, batch_files, attr_name, dedup)

            if verbose:
                batch_idx = batch_name.split('_')[1]
                echo('Batch {} of {} complete (size: {} files)'.format(
                    str(int(batch_idx)+1).rjust(2, '0'),
                    str(len(fname_batches)).rjust(2, '0'),
                    str(len(batch_files))
                ), indent=1, timestamp=True, fn_name="EXIF.run(..., wrapper='doni')")

            # exifmaster[batch_name] = exifd
            exifmaster.update(exifd)

        return exifmaster

    def set_exif(self, tags, values, verbose=False):
        """
        Overwrite EXIF attributes on a file or list of files.
        
        Arguments:
            tags {str} or {list} -- names of tags to overwrite
            values {str} or {list} -- values to set to `tags`
        
        Returns:
            nothing
        """

        # Get list of files and ensure tags and values are identical length
        target_files = [self.fname] if isinstance(self.fname, str) else self.fname
        tags = [tags] if isinstance(tags, str) else tags
        values = [values] if isinstance(values, str) or isinstance(values, int) else values
        assert len(tags) == len(values)
        
        # Check format of tags. Must be TagName, not tag_name
        if any(['-' in str(x) for x in tags]):
            echo("Invalid tag format. Proper tag format is 'TagName', not 'tag_name'",
                abort=True, fn_name='EXIF.set_exif')

        if verbose:
            if len(target_files) == 1:
                echo('Preparing to overwrite %s EXIF attributes for 1 file' % str(len(tags)), timestamp=True, fn_name='EXIF.set_exif')
            else:
                echo('Preparing to overwrite %s EXIF attributes for %s files' % \
                    (str(len(tags)), len(target_files)),
                    timestamp=True, fn_name='EXIF.set_exif')

        # Iterate over each file, and for each file iterate over each tag and
        # assign value to EXIF attribute
        for target_file in target_files:
            if verbose:
                echo("Altering EXIF for '%s'" % target_file,
                    timestamp=True, fn_name='EXIF.set_exif')
            for i in range(len(tags)):
                cmd = 'exiftool -overwrite_original -{}="{}" "{}"'.format(
                    tags[i], values[i], target_file)
                res = syscmd(cmd, encoding='utf-8')
                if 'nothing to do' in res.lower():
                    if verbose:
                        echo("Tag %s is invalid!" % tags[i], timestamp=True,
                            fn_name='EXIF.set_exif', indent=1, error=True)
                    else:
                        echo("Tag %s is invalid for file '%s'!" % (tags[i], target_file), error=True)
                else:
                    if verbose:
                        echo("Set attribute '%s' to value '%s'" % (tags[i], str(values[i])),
                            timestamp=True, fn_name='EXIF.set_exif', indent=1)

    def remove_exif(self, tags, verbose=False):
        """
        Remove EXIF attributes from a file or list of files.
        
        Arguments:
            tags {str} or {list} -- name(s) of tags to remove with `exiftool`
        
        Returns:
            nothing
        """

        # Get list of files and ensure tags and values are identical length
        target_files = [self.fname] if isinstance(self.fname, str) else self.fname
        tags = [tags] if isinstance(tags, str) else tags
        
        # Check format of tags. Must be TagName, not tag_name
        if any(['-' in str(x) for x in tags]):
            echo("Invalid tag format. Proper tag format is 'TagName', not 'tag_name'",
                abort=True, fn_name='EXIF.remove_exif')

        if verbose:
            if len(target_files) == 1:
                echo('Preparing to overwrite %s EXIF attributes for 1 file' % str(len(tags)), timestamp=True, fn_name='EXIF.remove_exif')
            else:
                echo('Preparing to overwrite %s EXIF attributes for %s files' % \
                    (str(len(tags)), len(target_files)),
                    timestamp=True, fn_name='EXIF.remove_exif')

        # Iterate over each file, and for each file iterate over each tag and
        # assign remove EXIF attribute
        for target_file in target_files:
            if verbose:
                echo("Altering EXIF for '%s'" % target_file,
                    timestamp=True, fn_name='EXIF.remove_exif')
            for i in range(len(tags)):
                cmd = 'exiftool -overwrite_original -{}= "{}"'.format(
                    tags[i], target_file)
                res = syscmd(cmd, encoding='utf-8')
                if 'nothing to do' in res.lower():
                    if verbose:
                        echo("Tag %s is invalid!" % tags[i], timestamp=True,
                            fn_name='EXIF.remove_exif', indent=1, error=True)
                    else:
                        echo("Tag %s is invalid for file '%s'!" % (tags[i], target_file), error=True)
                else:
                    if verbose:
                        echo("Removed attribute '%s'" % tags[i],
                            timestamp=True, fn_name='EXIF.remove_exif', indent=1)

    def rename_keys(self, key_dict):
        """
        Rename exif dictionary keys.
        
        Arguments:
            key_dict (dict): dictionary of key: value pairs where 'key' is current exif key name, and 'value' is desired key name
        
        Returns:
            {dict}

        Example:
            key_dict={'file_name': 'fname'} will result in the original key 'file_name' being
            renamed to 'fname'.
        """
        for k, v in key_dict.items():
            if k in self.exif.keys():
                self.exif[v] = self.exif.pop(k)
        return self.exif

    def coerce(self, key, val, fmt=['int', 'date', 'float'], onerror=['raise', 'null', 'revert']):
        """
        Attempt to coerce a dictionary value to specified type or format.
        
        Arguments:
            key {str} -- name of EXIF key
            fmt {str} -- format to coerce to, one of ['int', 'date', 'float']
            onerror {str} -- determine behavior if a value cannot be coerced
                - raise: raise an error (stop the program)
                - null: return None
                - revert: return original value
        Example:
            fmt='int':
                '+7' -> 7
                '-7' -> -7
        Example:
            fmt='date':
                '2018:02:29 01:28:10' -> ''2018-02-29 01:28:10''
        Example:
            fmt='float':
                '11.11' -> 11.11
        """

        def evalutate_error(val, onerror, e="Unable to coerce value"):
            """
            Handle error in any specified way, as described in parent function's docstring.

            Arguments:
                val {<any>} -- value to return if set to 'revert' mode
                onerror {str} -- dictate behavior of function, one of ['raise', 'null', 'revert']

            Keyword Arguments:
                e {str} -- error string to raise if run in 'raise' mode

            Returns:
                {str} -- if onerror='raise' -> error string
                {None} -- if onerror=None
                {${val}} -- if onerror='revert' -> original value
            """
            if onerror == 'raise':
                raise e
            elif onerror == 'null':
                return None
            elif onerror == 'revert':
                return val

        # Start by casting value as string
        if hasattr(self, 'exif'):
            val = str(self.exif[key])
        else:
            val = val

        # Coerce value
        if fmt == 'int':
            # Coerce value to integer
            val = val.replace('+', '') if re.match(r'^\+', val) else val
            val = val.replace(',', '') if ',' in val else val
            try:
                val = int(val)
            except Exception as e:
                val = evalutate_error(val, onerror, e)

        elif fmt == 'date':
            # Coerce value to date
            if DoniDt(val).is_exact():
                val = DoniDt(val).extract_first(apply_tz=True)
            else:
                val = evalutate_error(val, onerror,
                                      e="Unable to coerce value '{}' to type '{}'".format(val, fmt))

        elif fmt == 'float':
            # Coerce value to float
            val = val.replace('+', '') if re.match(r'^\+\d+', val) else val
            val = val.replace(',', '') if ',' in val else val
            try:
                val = float(val)
            except Exception as e:
                val = evalutate_error(val, onerror, e)

        return val


class FFmpeg(object):
    """
    Wrapper for FFmpeg BASH commands.
    """

    def __init__(self):
        pass

    def compress(self, f, outfile=None):
        """
        Arguments:
            f {str} or {list} -- file or files to compress

        Keyword Arguments:
            outfile {str} -- output file (default: {splitext(x)[0] + '-COMPRESSED' + splitext(x)[1]})

        Returns:
            nothing
        """
        if isinstance(f, str):
            f = [f]
        for x in f:
            outfile = splitext(x)[0] + '-COMPRESSED' + splitext(x)[1] if outfile is None else outfile
            cmd = 'ffmpeg -i "{}" -map 0:a:0 -b:a 32k "{}"'.format(x, outfile)
            syscmd(cmd)

    def join(self, audiofiles, targetfile):
        """
        Join multiple audio files into a single audio file using a direct call to ffmpeg.

        Arguments:
            audiofiles {list} -- list of audio filenames to join together
            targetfile {str} -- name of file to create from joined audio files

        Returns:
            nothing
        """

        assert isinstance(audiofiles, list)
        assert len(audiofiles) > 1

        # cmd = 'ffmpeg -i "concat:{}" -acodec copy "{}"'.format('|'.join(audiofiles), targetfile)
        
        tmpfile = join(
            dirname(audiofiles[0]),
            '.tmp.pydoni.audio.FFmpeg.join.txt'
        )

        with open(tmpfile, 'w') as f:
            for fname in audiofiles:
                f.write("file '%s'\n" % fname)
            f.write('')

        cmd = 'ffmpeg -f concat -safe 0 -i "%s" -c copy "%s"' % (tmpfile, targetfile)
        syscmd(cmd)
        if isfile(tmpfile):
            remove(tmpfile)
        return True

    def split(self, audiofile, segment_time):
        """
        Split audiofile into `segment_time` second size chunks.

        Arguments:
            audiofile {str} -- audiofile to split
            segment_time {int} -- desired number of seconds of each chunk

        Returns:
            nothing
        """
        # Split audio file with ffmpeg
        cmd = 'ffmpeg -i "{}" -f segment -segment_time {} -c copy "{}-ffmpeg-%03d{}"'.format(
            audiofile,
            segment_time,
            splitext(audiofile)[0],
            splitext(audiofile)[1])
        syscmd(cmd)

    def m4a_to_mp3(self, m4a_file):
        """
        Use ffmpeg to convert a .m4a file to .mp3.

        Arguments:
            m4a_file {str} -- path to file to convert to .mp3

        Returns:
            nothing
        """
        cmd = 'ffmpeg -i "{}" -codec:v copy -codec:a libmp3lame -q:a 2 "{}.mp3"'.format(
            m4a_file, splitext(m4a_file)[0])
        syscmd(cmd)


class Git(object):
    """
    House git command line function python wrappers.
    """

    def __init__(self):
        pass

    def is_git_repo(self):
        """
        Determine whether current dir is a git repository.

        Returns:
            {bool}
        """
        if '.git' in listdir():
            return True
        else:
            return False

    def status(self):
        """
        Return boolean based on output of 'git status' command. Return True if working tree is
        up to date and does not require commit, False if commit is required.
    
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
            fpath {str} or {list} -- file(s) to add
            all {bool} -- if True, execute 'git add .'
        
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


from pydoni.classes import DoniDt
from pydoni.pyobj import fmt_seconds, split_at, duplicated
from pydoni.vb import echo, clickfmt