class Attribute(object):
    def __init__(self):
        pass

    def __flatten__(self):
        """
        Combine all subattributes of an Attribute. If all lists, flatten to single
        list. If all strings, join into a list.
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

class GlobalVar(object):
    """
    Hold all program variables in a single Python object
    """
    def __init__(self):
        pass

class ProgramEnv(object):
    """
    Handle a temporary program environment for a Python program
    """
    def __init__(self, path, overwrite=False):
        import os, shutil, click
        from pydoni.vb import echo
        
        # Assign program environment path
        self.path = path
        if self.path == os.path.expanduser('~'):
            echo('Path cannot be home directory', abort=True)
        elif self.path == '/':
            echo('Path cannot be root directory', abort=True)
        
        # self.focus is the current working file, if specified
        self.focus = None
        
        # Overwrite existing directory if specified and directory exists
        if os.path.isdir(self.path):
            if overwrite:
                shutil.rmtree(self.path)
            else:
                if not click.confirm("Specified path {} already exists and 'overwrite' set to False. Continue with this path anyway?".format(self.path)):
                    echo('Quitting program', abort=True)
        if not os.path.isdir(self.path):
            os.mkdir(self.path)
    
    def copyfile(self, fname, set_focus=False):
        """
        Copy a file into the program environment.
        Args
            fname     (str) : filename to copy
            set_focus (bool): if True, set the focus to the newly-copied file
        Returns
            nothing
        """
        import os, shutil
        env_dest = os.path.join(self.path, os.path.basename(fname))
        shutil.copyfile(fname, env_dest)
        if set_focus:
            self.focus = env_dest
    
    def listfiles(self, path='.', pattern=None, full_names=False, recursive=False, ignore_case=True, include_hidden_files=False):
        """
        List files at given path.
        Args
            path (str): path to search for files in
            pattern ()
        """
        from pydoni.os import listfiles
        files = listfiles(path=path, pattern=pattern, full_names=full_names,
            recursive=recursive, ignore_case=ignore_case,
            include_hidden_files=include_hidden_files)
        return files
    
    def listdirs(self, path='.', full_names=False):
        """List directories at given path"""
        from pydoni.os import listdirs
        return listdirs(path=path, full_names=full_names)
    
    def downloadfile(self, url, destfile):
        """Download a file to environment"""
        import requests, shutil
        r = requests.get(url, stream=True)
        with open(destfile, 'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)
    
    def unarchive(fpath):
        """Extract a .zip archive to the same directory"""
        import zipfile, os
        dest_dir = os.path.dirname(fpath)
        with zipfile.ZipFile(fpath, 'r') as zip_ref:
            zip_ref.extractall(dest_dir)
    
    def delete_env(self):
        import shutil
        from os import chdir
        from os.path import dirname
        chdir(dirname(self.path))
        shutil.rmtree(self.path)

class Audio(object):
    """Operate on an audio file"""
    def __init__(self, fname):
        import os
        self.fname = fname
        self.fmt = os.path.splitext(self.fname)[1].replace('.', '').lower()
    def convert(self, dest_fmt, verbose=False):
        """Convert an audio file to destination format and write with identical filename"""
        import os
        from pydub import AudioSegment
        from pydoni.vb import echo
        echo("Converting input file to format '{}'".format(dest_fmt)) if verbose else None
        if self.fmt == 'mp3' and dest_fmt == 'wav':
            sound = AudioSegment.from_mp3(self.fname)
        elif self.fmt == 'wav' and dest_fmt == 'mp3':
            sound = AudioSegment.from_wav(self.fname)
        else:
            from pydoni.vb import echo
            echo('Must convert to/from either mp3 or wav', abort=True)
        outfile = os.path.splitext(self.fname)[0] + '.' + dest_fmt
        sound.export(outfile, format=dest_fmt)
        self.fname = outfile
        self.fmt = dest_fmt
        return None
    def split(self, segment_time=55, verbose=False):
        """Split audio file into segments of given length using ffmpeg"""
        import os, re
        from pydoni.sh import syscmd
        from pydoni.os import listfiles
        from pydoni.vb import echo
        echo("Duration longer than 55 seconds, splitting audio file with ffmpeg") if verbose else None
        # dirname = os.path.dirname(self.fname)
        cmd = 'ffmpeg -i "{}" -f segment -segment_time {} -c copy "{}-ffmpeg-%03d{}"'.format(
            self.fname, segment_time,
            os.path.splitext(self.fname)[0],
            os.path.splitext(self.fname)[1])
        res = syscmd(cmd)
        self.fnames_split = listfiles(pattern=r'ffmpeg-\d{3}\.%s' % self.fmt)
        return None
    def join(self, audiofiles, silence_between=1000):
        """Join multiple audio files into a single file and return the output filename
        audiofiles: list of filenames to concatenate
        silence_between: amount of silence to insert between clips in miliseconds"""
        import os, re
        from pydub import AudioSegment
        from pydoni.pyobj import systime
        from pydoni.vb import echo
        sound = AudioSegment.silent(duration=1)
        audiofiles = [self.fname] + audiofiles
        for fname in audiofiles:
            ext = os.path.splitext(fname)[1].lower().replace('.', '')
            if ext == 'mp3':
                fnamesound = AudioSegment.from_mp3(fname)
            elif ext == 'wav':
                fnamesound = AudioSegment.from_wav(fname)
            else:
                from pydoni.vb import echo
                echo('Invalid audio file {}, must be either mp3 or wav'.format(fname), abort=True)
            sound = sound + fnamesound
            if silence_between > 0:
                sound = sound + AudioSegment.silent(duration=silence_between)
        outfile = '{}-Audio-Concat-{}-Files{}'.format(
            systime(stripchars=True),
            str(len(audiofiles)),
            os.path.splitext(self.fname)[1])
        sound.export(outfile, format='mp3')
        self.fname = outfile
        return None
    def set_google_credentials(self, google_application_credentials_json):
        """Set environment variable as path to Google credentials JSON file"""
        import os
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_application_credentials_json
    def transcribe(self, verbose=False):
        """Transcribe the given audio file using Google Cloud Speech Recognition"""
        import re, os, tqdm
        from google.cloud import speech_v1p1beta1 as speech
        from pydoni.vb import echo
        # Convert audio file to wav if mp3
        if self.fmt == 'mp3':
            self.convert('wav', verbose=verbose)
        # Split audio file into segments if longer than 60 seconds
        if self.get_duration() > 55:
            self.split(55, verbose=verbose)
        echo('Transcribing audio file') if verbose else None
        fnames_transcribe = self.fnames_split if hasattr(self, 'fnames_split') else [self.fname]
        client = speech.SpeechClient()
        transcript = []
        for fname in tqdm.tqdm(fnames_transcribe):
            with open(fname, 'rb') as audio_file:
                content = audio_file.read()
            audio = speech.types.RecognitionAudio(content=content)
            config = speech.types.RecognitionConfig(
                encoding=speech.enums.RecognitionConfig.AudioEncoding.LINEAR16,
                # sample_rate_hertz=400,
                language_code='en-US',
                audio_channel_count=2,
                enable_separate_recognition_per_channel=False)
            response = client.recognize(config, audio)
            # Each result is for a consecutive portion of the audio. Iterate through
            # them to get the transcripts for the entire audio file.
            for result in response.results:
                # The first alternative is the most likely one for this portion.
                transcript.append(result.alternatives[0].transcript)
        # De-capitalize first letter of each transcript. This happens as a long audio segment is
        # broken into smaller clips, the first word in each of those clips becomes capitalized.
        transcript = [x[0].lower() + x[1:] for x in transcript]
        transcript = re.sub(r' +', ' ', ' '.join(transcript)).strip()
        self.transcript = transcript
        return transcript
    def apply_transcription_corrections(self, transcript=None):
        """Apply any and all corrections to output of self.transcribe()"""
        if not transcript:
            if not hasattr(self, 'transcript'):
                from pydoni.vb import echo
                echo('Must create transcript before calling Audio.apply_smart_dictation_corrections.smart_dictation()! Try running Audio.transcribe() first', error=True)
                return None
            else:
                transcript = self.transcript
        def smart_dictation(transcript):
            """Apply corrections to spoken keywords like 'comma', 'period' or 'quote'/'unquote'"""
            import re
            dictation_map = {
                r'(\b|\s)(comma)(\s|\b)'            : r',\3',
                r'(\b|\s)(colon)(\s|\b)'            : r':\3',
                r'(\b|\s)(semicolon)(\s|\b)'        : r';\3',
                r'(\b|\s)(period)(\s|\b)'           : r'.\3',
                r'(\b|\s)(exclamation point)(\s|\b)': r'!\3',
                r'(\b|\s)(question mark)(\s|\b)'    : r'?\3',
                r'(\b|\s)(unquote)(\s|\b)'          : r'"\3',
                r'(\b|\s)(end quote)(\s|\b)'        : r'"\3',
                r'(\b|\s)(quote)(\s|\b)'            : r'\1"',
                r'(\b|\s)(hyphen)(\s|\b)'           : '-',
                ' , '                               : ', ',
                r' \. '                               : '. ',
                r'(\b|\s)(tab)(\s|\b)'              : '  ',
                r'( *)(new line)( *)'               : '\n',
                r'( *)(newline)( *)'                : '\n',
                r'(\b|\s)(tag title)\n'             : r'\1<title>\n',
                r'(\b|\s)(tag heading)\n'           : r'\1<h>\n',
                r'(\b|\s)(tag emphasis)\n'          : r'\1<em>\n',
                r'(\b|\s)(emphasis)\n'              : r'\1<em>\n',
                r'(\b|\s)(tag emphasized)\n'        : r'\1<em>\n',
                r'(\b|\s)(emphasized)\n'            : r'\1<em>\n'}
            for string, replacement in dictation_map.items():
                transcript = re.sub(string, replacement, transcript, flags=re.IGNORECASE)
            return transcript
        def smart_capitalize(transcript):
            """Capitalize transcript intelligently"""
            import re
            from pydoni.pyobj import capNthChar, replaceNthChar, insertNthChar
            # Capitalize first letter of each sentence, split by newline character
            val = transcript
            val = '\n'.join([capNthChar(x, 0) for x in val.split('\n')])
            # Capitalize word following keyphrase 'make capital'
            cap_idx = [m.start()+len('make capital')+1 for m in re.finditer('make capital', val)]
            if len(cap_idx):
                for idx in cap_idx:
                    val = capNthChar(val, idx)
                val = val.replace('make capital ', '')
            # Capitalize and concatenate letters following keyphrase 'make letter'. Ex: 'make letter a' -> 'A'
            letter_idx = [m.start()+len('make letter')+1 for m in re.finditer('make letter', val)]
            if len(letter_idx):
                for idx in letter_idx:
                    val = capNthChar(val, idx)
                    val = replaceNthChar(val, idx+1, '.')
                    if idx == letter_idx[len(letter_idx)-1]:
                        val = insertNthChar(val, idx+2, ' ')
                val = val.replace('make letter ', '')
            # Capitalize letter following '?'
            if '? ' in val:
                q_idx = [m.start()+len('? ') for m in re.finditer(r'\? ', val)]
                for idx in q_idx:
                    val = capNthChar(val, idx)
            return val
        def excess_spaces(transcript):
            import re
            return re.sub(r' +', ' ', transcript)
        def manual_corrections(transcript):
            """Apply manual corrections to transcription"""
                # Regex word replacements
            import re
            dictation_map = {
                r'(\b)(bye bye)(\b)'    : 'Baba',
                r'(\b)(Theon us)(\b)'   : "Thea Anna's",
                r'(\b)(Theon as)(\b)'   : "Thea Anna's",
                r'(\b)(the ana\'s)(\b)' : "Thea Anna's",
                r'(\b)(the ionos)(\b)'  : "Thea Anna's",
                # Capitalize first letter of sentence following tab indentation,
                r'\n([A-Za-z])'         : lambda x: '\n' + x.groups()[0].upper(),
                r'\n  ([A-Za-z])'       : lambda x: '\n  ' + x.groups()[0].upper(),
                r'\n    ([A-Za-z])'     : lambda x: '\n    ' + x.groups()[0].upper(),
                r'\n      ([A-Za-z])'   : lambda x: '\n      ' + x.groups()[0].upper(),
                r'\n        ([A-Za-z])' : lambda x: '\n        ' + x.groups()[0].upper(),
                r"s\'s"                 : "s'",
                'grace'                 : 'Grace',
                'the west'              : 'the West',
                'The west'              : 'The West',
                'on certain'            : 'uncertain',
                'advent'                : 'advent'}
            for string, replacement in dictation_map.items():
                transcript = re.sub(string, replacement, transcript, flags=re.IGNORECASE)
            return transcript
        self.transcript = smart_dictation(self.transcript)
        self.transcript = smart_capitalize(self.transcript)
        self.transcript = excess_spaces(self.transcript)
        self.transcript = manual_corrections(self.transcript)
    def get_duration(self):
        """Get the duration of audio file"""
        import wave
        import contextlib
        with contextlib.closing(wave.open(self.fname, 'r')) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            duration = frames / float(rate)
        self.duration = duration
        return duration


class Movie(object):
    def __init__(self, fname):
        import re
        from pydoni.os import getFinderComment
        self.fname = fname
        (self.title, self.year, self.ext) = self.parse_movie_year_ext()
        self.omdb_populated = False  # Will be set to True if self.query_omdb() is successful
    def parse_movie_year_ext(self):
        import re, os
        ext       = os.path.splitext(self.fname)[1]
        movie     = os.path.splitext(self.fname)[0]
        rgx_movie = r'^(.*?)\((\d{4})\)'
        title     = re.sub(rgx_movie, r'\1', movie).strip()
        year      = re.sub(rgx_movie, r'\2', movie)
        return (title, year, ext)
    def query_omdb(self):
        import omdb
        try:
            met = omdb.get(title=self.title, year=self.year, fullplot=False, tomatoes=False)
            met = None if not len(met) else met
            if met:
                for key, val in met.items():
                    setattr(self, key, val)
                self.parse_ratings()
                self.manual_clean_values()
                self.omdb_populated = True
                del self.title, self.year, self.ext
        except:
            self.omdb_populated = False  # Query unsuccessful
    def parse_ratings(self):
        import re, numpy as np
        if len(self.ratings):
            for rating in self.ratings:
                source = rating['source']
                if source.lower() not in ['internet movie database', 'rotten tomatoes', 'metacritic']:
                    continue
                source = re.sub('internet movie database', 'rating_imdb', source, flags=re.IGNORECASE)
                source = re.sub('rotten tomatoes', 'rating_rt', source, flags=re.IGNORECASE)
                source = re.sub('metacritic', 'rating_mc', source, flags=re.IGNORECASE)
                source = source.replace(' ', '')
                value = rating['value']
                value = value.replace('/100', '')
                value = value.replace('/10', '')
                value = value.replace('%', '')
                value = value.replace('.', '')
                value = value.replace(',', '')
                setattr(self, source, value)
        self.rating_imdb = np.nan if not hasattr(self, 'rating_imdb') else self.rating_imdb
        self.rating_rt   = np.nan if not hasattr(self, 'rating_rt') else self.rating_rt
        self.rating_mc   = np.nan if not hasattr(self, 'rating_mc') else self.rating_mc
        if hasattr(self, 'ratings'):
            del self.ratings
        if hasattr(self, 'imdb_rating'):
            del self.imdb_rating
        if hasattr(self, 'metascore'):
            del self.metascore
    def manual_clean_values(self):
        def convert_to_int(value):
            import numpy as np
            if isinstance(value, int):
                return value
            try:
                return int(value.replace(',', '').replace('.', '').replace('min', '').replace(' ', '').strip())
            except:
                return np.nan
        def convert_to_datetime(value):
            import numpy as np
            from datetime import datetime
            if not isinstance(value, str):
                return np.nan
            try:
                return datetime.strptime(value, '%d %b %Y').strftime('%Y-%m-%d')
            except:
                return np.nan
        for attr in ['rating_imdb', 'rating_mc', 'rating_rt', 'imdb_votes', 'runtime']:
            if hasattr(self, attr):
                setattr(self, attr, convert_to_int(getattr(self, attr)))
        self.released = convert_to_datetime(self.released)
        self.dvd      = convert_to_datetime(self.dvd)
        self.replace_value('N/A', np.nan)
        if self.response == 'True':
            self.response = True
        elif self.response == 'False':
            self.response = False
        else:
            self.response = np.nan
    def replace_value(self, value, replacement):
        for key, val in self.__dict__.items():
            if val == value:
                setattr(self, key, replacement)

class DoniDt(object):
    """Custom date/datetime handling. By default:
        * Miliseconds will be deleted"""
    def __init__(self, val, apply_tz=True):
        from pydoni.classes import Attribute
        self.val = str(val)
        sep = r'\.|\/|-|_|\:'
        rgx = Attribute()
        rgx.d = r'(?P<year>\d{4})(%s)(?P<month>\d{2})(%s)(?P<day>\d{2})' % (sep, sep)
        rgx.dt = r'%s(\s+)(?P<hours>\d{2})(%s)(?P<minutes>\d{2})(%s)(?P<seconds>\d{2})' % (rgx.d, sep, sep)
        rgx.dt_tz = r'%s(?P<tz_sign>-|\+)(?P<tz_hours>\d{1,2})(:)(?P<tz_minutes>\d{1,2})' % (rgx.dt)
        rgx.dt_ms = r'%s\.(?P<miliseconds>\d+)$' % (rgx.dt)
        self.rgx = rgx
        self.dtype, self.match = self.detect_dtype()
    def is_exact(self):
        """Test if input string is exactly a date or datetime value, returns bool"""
        import re
        m = [bool(re.search(pattern, self.val)) for pattern in \
            ['^' + x + '$' for x in  self.rgx.__flatten__()]]
        return any(m)
    def contains(self):
        """Test if input string contains a date or datetime value, returns bool"""
        import re
        m = [bool(re.search(pattern, self.val)) for pattern in self.rgx.__flatten__()]
        return any(m)
    def extract_first(self, apply_tz=True):
        """Given a string with a date or datetime value, extract the FIRST datetime
        value as string"""
        import re, datetime
        from pydoni.vb import echo
        val = self.val
        val = str(val).strip() if not isinstance(val, str) else val.strip()
        if self.match:
            m = self.match
            if self.dtype == 'dt_tz':
                dt = '{}-{}-{} {}:{}:{}'.format(
                    m.group('year'), m.group('month'), m.group('day'),
                    m.group('hours'), m.group('minutes'), m.group('seconds'))
                tz = '{}{}:{}'.format(m.group('tz_sign'),
                    m.group('tz_hours'), m.group('tz_minutes'))
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
                    self.dtype = 'dt'
                    return dt
            elif self.dtype == 'dt':
                dt = '{}-{}-{} {}:{}:{}'.format(
                    m.group('year'), m.group('month'), m.group('day'),
                    m.group('hours'), m.group('minutes'), m.group('seconds'))
                self.dtype = 'dt'
                return dt
            elif self.dtype == 'd':
                dt = '{}-{}-{}'.format(m.group('year'), m.group('month'), m.group('day'))
                self.dtype = 'd'
                return dt
        else:
            return val
    def detect_dtype(self):
        """Get datatype as one of 'd', 'dt', 'dt_tz', and return regex match object"""
        import re
        if re.search(self.rgx.dt_tz, self.val):
            return ('dt_tz', re.search(self.rgx.dt_tz, self.val))
        elif re.search(self.rgx.dt, self.val):
            return ('dt', re.search(self.rgx.dt, self.val))
        elif re.search(self.rgx.d, self.val):
            return ('d', re.search(self.rgx.d, self.val))
        else:
            return (None, None)

class EXIF(object):
    """Extract and handle EXIF metadata from file"""
    def __init__(self, fname):
        self.fname = fname
    def run(self):
        from pydoni.sh import exiftool
        self.exif = exiftool(self.fname)
        return self.exif
    def rename_keys(self, key_dict):
        """Rename exif dictionary keys. Ex: key_dict={'file_name': 'fname'} will result in the
        original key 'file_name' being renamed to 'fname'"""
        for k, v in key_dict.items():
            if k in self.exif.keys():
                self.exif[v] = self.exif.pop(k)
    def coerce(self, key, val, fmt=['int', 'date', 'float'], onerror=['raise', 'null', 'revert']):
        """Attempt to coerce a dictionary value to specified type or format
        Parameters:
            key: name of EXIF key
            fmt: format to coerce to
            onerror: determine behavior if a value cannot be coerced
                - raise: raise an error (stop the program)
                - null: return None
                - revert: return original value
        Examples:
        fmt='int':
            '+7' -> 7
            '-7' -> -7
        fmt='date':
            '2018:02:29 01:28:10' -> ''2018-02-29 01:28:10''
        fmt='float':
            '11.11' -> 11.11
        """
        import re
        from pydoni.classes import DoniDt
        if hasattr(self, 'exif'):
            val = str(self.exif[key])  # Start by casting value as string
        else:
            val = val
        def evalutate_error(val, onerror, e="Unable to coerce value"):
            if onerror == 'raise':
                raise e
            elif onerror == 'null':
                return None
            elif onerror == 'revert':
                return val
        if fmt == 'int':
            val = val.replace('+', '') if re.match(r'^\+', val) else val
            val = val.replace(',', '') if ',' in val else val
            try:
                val = int(val)
            except Exception as e:
                val = evalutate_error(val, onerror, e)
        elif fmt == 'date':
            if DoniDt(val).is_exact():
                val = DoniDt(val).extract_first(apply_tz=True)
            else:
                val = evalutate_error(val, onerror,
                    e="Unable to coerce value '{}' to type '{}'".format(val, fmt))
        elif fmt == 'float':
            val = val.replace('+', '') if re.match(r'^\+\d+', val) else val
            val = val.replace(',', '') if ',' in val else val
            try:
                val = float(val)
            except Exception as e:
                val = evalutate_error(val, onerror, e)
        return val

class Git(object):
    """House git command line function python wrappers"""
    
    def __init__(self):
        pass

    def status(self):
        """Return boolean based on output of 'git status' command. Return True if working tree is
        up to date and does not require commit, False if commit is required."""
        from pydoni.sh import syscmd
        out = syscmd('git status').decode()
        working_tree_clean = "On branch masterYour branch is up to date with 'origin/master'.nothing to commit, working tree clean"
        not_git_repo = 'fatal: not a git repository (or any of the parent directories): .git'
        if out.replace('\n', '') == working_tree_clean:
            return True
        elif out.replace('\n', '') == not_git_repo:
            return None
        else:
            return False

    def add(self, all=True):
        import subprocess
        if all == True:
            out = subprocess.call('git add .;', shell=True)

    def commit(self, msg):
        import subprocess
        out = subprocess.call("git commit -m '{}';".format(msg), shell=True)

    def push(self):
        import subprocess
        out = subprocess.call("git push;", shell=True)