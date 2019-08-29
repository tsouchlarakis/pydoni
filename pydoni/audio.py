import contextlib
import wave
import re
import numpy as np
from os import environ, chdir, getcwd
from os.path import isfile, splitext, join, expanduser, dirname, basename
from pydub import AudioSegment
from google.cloud import speech_v1p1beta1 as speech
from tqdm import tqdm


class Audio(object):
    """
    Operate on an audio file.

    Arguments:
        audiofile {str} -- path to audio file
    """

    def __init__(self, audiofile):
        
        assert isfile(audiofile)

        # Set filename and extension
        self.audiofile = audiofile
        self.ext = splitext(self.audiofile)[1]

        # Read audio file as AudioSegement
        if self.ext.lower() == '.mp3':
            self.sound = AudioSegment.from_mp3(self.audiofile)
        elif self.ext.lower() == '.wav':
            self.sound = AudioSegment.from_wav(self.audiofile)
        else:
            self.sound = AudioSegment.from_file(self.audiofile)

        # Get duration of audio segment
        try:
            if self.ext.lower() != '.wav':
                self.convert(dest_fmt='wav')
                self.duration = get_duration(splitext(self.audiofile)[0] + '.wav')
            else:
                self.duration = self.get_duration()
        except Exception as e:
            echo('Unable to get audio duration!', warn=True, fn_name='pydoni.Audio.__init__', error_msg=str(e))
            self.duration = None

    def split(self, segment_time):
        """
        Wrapper for pydoni.audio.split_audiofile().
        """
        return split_audiofile(self.audiofile, segment_time)

    def get_duration(self):
        """
        Wrapper for pydoni.audio.get_duration().
        """
        return get_duration(self.audiofile)

    def compress(self, outfile=None):
        """
        Export audio file at low bitrate (92kbps) as an mp3.
        
        Arguments:
            audiofile {str} -- path to audiofile to compress

        Keyword Arguments:
            outfile {str} -- path to output file to write. If None, replace `audiofile` on disk (default: {None})

        Returns:
            nothing
        """
        outfile = self.audiofile if outfile is None else outfile
        self.sound.export(outfile, bitrate=92)

    def set_channels(self, num_channels):
        """
        Wrapper for pydub.AudioSegment.set_channels().

        Arguments:
            num_channels {int} -- number of channels to convert audio segment to using pydub.AudioSegment.set_channels() (default: {None})

        Returns:
            nothing
        """
        self.sound = self.sound.set_channels(num_channels)

    def convert(self, dest_fmt, num_channels=None):
        """
        Convert an audio file to destination format and write with identical filename with `pydub`.
        
        Arguments:
            dest_fmt {str} -- desired output format, one of ['mp3', 'wav']
        
        Keyword Arguments:
            update_self {bool} -- if True, set `self.fname` and `self.ext` to converted file and file format after conversion (default: {True})
            num_channels {int} -- number of channels to convert audio segment to using pydub.AudioSegment.set_channels() (default: {None})
        
        Returns:
            nothing
        """

        dest_fmt = dest_fmt.replace('.', '')
        assert dest_fmt in ['mp3', 'wav']
        assert self.ext != dest_fmt
        outfile = splitext(self.audiofile)[0] + '.' + dest_fmt
        assert not isfile(outfile)

        if num_channels is not None:
            if isinstance(num_channels, int):
                self.set_channels(num_channels)

        self.sound.export(outfile, format=dest_fmt)

    def transcribe(self, method='gcs', gcs_split_threshold=55, apply_correction=True, verbose=True):
        """
        Wrapper for pydoni.audio.transcribe().
        """
        return transcribe(
            audiofile=self.audiofile,
            gcs_split_threshold=gcs_split_threshold,
            apply_correction=apply_correction,
            verbose=verbose)


def transcribe(audiofile, method='gcs', gcs_split_threshold=50, apply_correction=True, verbose=False):
    """
    Transcribe audio file in .wav format using method of choice.

    Arguments:
        audiofile {str} -- audio file to transcribe

    Keyword Arguments:
        method {str} -- method to use for audiofile transcription, one of ['gcs']
        gcs_split_threshold {int} -- maximum audio clip size in seconds, if clip exceeds this length it will be split using class method `split()` (default: {55})
        apply_correction {bool} -- if True, call `self.apply_transcription_corrections()` after transcript created (default: {True})
        verbose {bool} -- if True, print progress messages to console (default: {True})

    Returns:
        {str} -- transcription string
    """

    assert method in ['gcs']
    fn_name = 'pydoni.audio.transcribe'

    # Copy `audiofile` to temporary program environment
    wd = join(expanduser('~'), '.tmp.pydoni.transcribe')
    if verbose:
        echo("Creating temporary environment at '%s'" % wd, fn_name=fn_name, timestamp=True)
    env = ProgramEnv(wd, overwrite=True)
    if verbose:
        echo("Copying file '%s' to environment" % audiofile, fn_name=fn_name, timestamp=True)
    env.copyfile(audiofile, set_focus=True)
    # chdir(env.path)

    try:
        if method == 'gcs':

            if 'GOOGLE_APPLICATION_CREDENTIALS' not in environ.keys():
                echo("Must run 'set_google_credentials()' before running GCS transcription!", abort=True)

            # Ensure file is in .wav format. If not, create a temporary .wav file
            ext = splitext(env.focus)[1]
            if ext.lower() != '.wav':
                if verbose:
                    echo('Converting audio to .wav', timestamp=True, fn_name=fn_name)
                fname = splitext(env.focus)[0] + '.wav'
                audio = Audio(env.focus)
                audio.set_channels(1)
                audio.sound.export(fname, format='wav')
                env.focus = fname

            # Split audio file into segments if longer than `gcs_split_threshold` seconds
            duration = get_duration(env.focus)
            if isinstance(duration, int) or isinstance(duration, float):
                if np.floor(duration) > gcs_split_threshold:
                    if verbose:
                        echo('Splitting audio into %s second chunks' % gcs_split_threshold,
                            timestamp=True, fn_name=fn_name)
                    fnames = split_audiofile(env.focus, segment_time=gcs_split_threshold)
                else:
                    fnames = [env.focus]
            else:
                fnames = [env.focus]

            # Set up transcription
            transcript = []
            client = speech.SpeechClient()

            # Loop over files to transcribe and apply Google Cloud transcription
            if verbose:
                echo('Transcribing audio', timestamp=True, fn_name=fn_name)
                iter = tqdm(fnames)
            else:
                iter = fnames
            try:
                for fname in iter:
                    with open(fname, 'rb') as audio_file:
                        content = audio_file.read()
                        aud = speech.types.RecognitionAudio(content=content)
                        config = speech.types.RecognitionConfig(
                            encoding=speech.enums.RecognitionConfig.AudioEncoding.LINEAR16,
                            # sample_rate_hertz=400,
                            language_code='en-US',
                            audio_channel_count=1,
                            enable_separate_recognition_per_channel=False
                        )
                        response = client.recognize(config, aud)
                    
                    # Each result is for a consecutive portion of the audio. Iterate through
                    # them to get the transcripts for the entire audio file.
                    for result in response.results:
                        # The first alternative is the most likely one for this portion.
                        transcript.append(result.alternatives[0].transcript)

            except Exception as e:
                env.delete_env()
                echo('Transcription failed! Temporary program environment deleted!', error=True)
                raise e

            # De-capitalize first letter of each transcript. This happens as a long audio segment is
            # broken into smaller clips, the first word in each of those clips becomes capitalized.
            if 'transcript' in locals():
                if isinstance(transcript, list):
                    transcript = [x[0].lower() + x[1:] for x in transcript]
                    transcript = re.sub(r' +', ' ', ' '.join(transcript)).strip()

                    # Apply transcription corrections if specified
                    if apply_correction:
                        transcript = apply_transcription_corrections(transcript)
                    
                else:
                    env.delete_env()
                    echo('Unable to transcribe audio file!', abort=True)
            else:
                env.delete_env()
                echo('Unable to transcribe audio file!', abort=True)
        
    except Exception as e:
        env.delete_env()
        echo('Transcription failed! Temporary program environment deleted!', error=True)
        raise e

    env.delete_env()
    return transcript


def apply_transcription_corrections(transcript):
    """
    Apply any and all corrections to output of `self.transcribe()`.

    Arguments:
        transcript {str} -- transcript string to apply corrections to

    Returns:
        {str} -- transcript string with corrections
    """

    def smart_dictation(transcript):
        """
        Apply corrections to spoken keywords like 'comma', 'period' or 'quote'/'unquote'.
        
        Arguments:
            transcript {str} -- transcript string
        
        Returns:
            {str} -- transcript string
        """
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
        """
        Capitalize transcript intelligently according to the following methods:
            1. Capitalize first letter of each sentence, split by newline character.
            2. Capitalize word following keyphrase 'make capital'.
            3. Capitalize word and concatenate letters following keyphrase 'make letter'.
            4. Capitalie letter following '?'.
        
        Arguments:
            transcript {str} -- transcript string
        
        Returns:
            {str} -- transcript string
        """
        
        # Capitalize first letter of each sentence, split by newline character
        val = transcript
        val = '\n'.join([cap_nth_char(x, 0) for x in val.split('\n')])
        
        # Capitalize word following keyphrase 'make capital'
        cap_idx = [m.start()+len('make capital')+1 for m in re.finditer('make capital', val)]
        if len(cap_idx):
            for idx in cap_idx:
                val = cap_nth_char(val, idx)
            val = val.replace('make capital ', '')
        
        # Capitalize and concatenate letters following keyphrase 'make letter'. Ex: 'make letter a' -> 'A'
        letter_idx = [m.start()+len('make letter')+1 for m in re.finditer('make letter', val)]
        if len(letter_idx):
            for idx in letter_idx:
                val = cap_nth_char(val, idx)
                val = replace_nth_char(val, idx+1, '.')
                if idx == letter_idx[len(letter_idx)-1]:
                    val = insert_nth_char(val, idx+2, ' ')
            val = val.replace('make letter ', '')
        
        # Capitalize letter following '?'
        if '? ' in val:
            q_idx = [m.start()+len('? ') for m in re.finditer(r'\? ', val)]
            for idx in q_idx:
                val = cap_nth_char(val, idx)
        return val

    def excess_spaces(transcript):
        """
        Replace extra spaces with a single space.
        
        Arguments:
            transcript {str} -- transcript string
        
        Returns:
            {str} -- transcript string
        """
        return re.sub(r' +', ' ', transcript)

    def manual_corrections(transcript):
        """
        Apply manual corrections to transcription.
        
        Arguments:
            transcript {str} -- transcript string
        
        Returns:
            {str} -- transcript string
        """

        # Regex word replacements
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

    # Apply all correction methods    
    transcript = smart_dictation(transcript)
    transcript = smart_capitalize(transcript)
    transcript = excess_spaces(transcript)
    transcript = manual_corrections(transcript)

    return transcript


def join_audiofiles_ffmpeg(audiofiles, targetfile):
    """
    Join multiple audio files into a single audio file using a direct call to ffmpeg.

    Arguments:
        audiofiles {list} -- list of audio filenames to join together
        targetfile {str} -- name of file to create from joined audio files

    Returns:
        {bool} -- True if successful, False if not
    """

    cmd = 'ffmpeg -i "concat:{}" -acodec copy "{}"'.format('|'.join(audiofiles), targetfile)
    try:
        syscmd(cmd) 
        return True

    except Exception as e:
        echo(e)
        return False


def join_audiofiles_pydub(audiofiles, targetfile, silence_between):
    """
    Join multiple audio files into a single audio file using pydub.

    Arguments:
        audiofiles {list} -- list of audio filenames to join together
        targetfile {str} -- name of file to create from joined audio files
    
    Keyword Arguments:
        silence_between {int} -- milliseconds of silence to insert between clips (default: {0})

    Returns:
        {bool} -- True if successful, False if not
    """

    for file in audiofiles:
        ext = splitext(file)[1].lower()
        assert ext in ['.mp3', '.wav']

    try:
        # Create sound object, initialize with 1ms of silence
        sound = AudioSegment.silent(duration=1)
        
        # Iterate over list of audio files and join audio
        for file in audiofiles:
            ext = splitext(file)[1].lower()
            fnamesound = AudioSegment.from_mp3(file) if ext == '.mp3' else AudioSegment.from_wav(file)
            sound = sound + fnamesound
            if silence_between > 0:
                sound = sound + AudioSegment.silent(duration=silence_between)

        sound.export(targetfile, format='mp3')
        return True
        
    except Exception as e:
        echo(e)
        return False


def join_audiofiles(audiofiles, targetfile, method=None, silence_between=0):
    """
    Join multiple audio files into a single audio file.

    Arguments:
        audiofiles {list} -- list of audio filenames to join together
        targetfile {str} -- name of file to create from joined audio files
    
    Keyword Arguments:
        method {str} -- method to join audiofiles, one of ['ffmpeg', 'pydub']. If None, method is automatically determined
        silence_between {int} -- milliseconds of silence to insert between clips (default: {0})

    Returns:
        {bool} -- True if run successfully, False otherwise
    """

    assert isinstance(silence_between, int)
    assert isinstance(audiofiles, list)
    assert len(audiofiles) > 1
    for fname in audiofiles:
        assert isfile(fname)

    if method is None:
        if silence_between == 0:
            method = 'ffmpeg'
        else:
            method = 'pydub'
    assert method in ['ffmpeg', 'pydub']

    if method == 'ffmpeg':
        out = join_audiofiles_ffmpeg(audiofiles, targetfile)
    else:
        out = join_audiofiles_pydub(audiofiles, targetfile, silence_between)

    return out


def split_audiofile(audiofile, segment_time):
    """
    Split audio file into segments of given length using ffmpeg.
    
    Arguments:
        audiofile {str} -- path to audio file to split
        segment_time {int} -- length of split audio clips in seconds to split audio file into if length is too long
    
    Returns:
        {list} -- list of split filenames
    """

    assert isfile(audiofile)
    assert isinstance(segment_time, int)
    wd = getcwd()

    # Split audio file with ffmpeg
    cmd = 'ffmpeg -i "{}" -f segment -segment_time {} -c copy "{}-ffmpeg-%03d{}"'.format(
        audiofile,
        segment_time,
        splitext(audiofile)[0],
        splitext(audiofile)[1]
    )
    syscmd(cmd)

    # Return resulting files under `fnames_split` attribute
    dname = dirname(audiofile)
    dname = '.' if dname == '' else dname
    chdir(dname)
    splitfiles = listfiles(
        path=dname,
        pattern=r'%s-ffmpeg-\d{3}\.%s' % \
            (basename(splitext(audiofile)[0]), splitext(audiofile)[1].replace('.', ''))
    )
    if dname != '.':
        splitfiles = [join(dname, x) for x in splitfiles]

    chdir(wd)
    return splitfiles


def get_duration(audiofile):
    """
    Get the duration of audio file.
    
    Arguments:
        audiofile {str} -- path to audio file to get duration of

    Returns:
        {float} -- duration of audio file in seconds
    """

    assert isfile(audiofile)
    assert splitext(audiofile)[1].lower() == '.wav'

    with contextlib.closing(wave.open(audiofile, 'r')) as f:
        frames = f.getnframes()
        rate = f.getframerate()
        duration = frames / float(rate)
    
    return duration


def set_google_credentials(google_application_credentials_json):
    """
    Set environment variable as path to Google credentials JSON file.
    
    Arguments:
        google_application_credentials_json {str} -- path to google application credentials file

    Returns:
        nothing
    """
    assert(isfile(google_application_credentials_json))
    environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_application_credentials_json


from pydoni.sh import syscmd
from pydoni.vb import echo
from pydoni.os import listfiles
from pydoni.classes import ProgramEnv
from pydoni.pyobj import cap_nth_char, replace_nth_char, insert_nth_char
