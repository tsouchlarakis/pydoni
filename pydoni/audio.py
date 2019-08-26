from os.path import isfile
from pydoni.sh import syscmd
from pydoni.vb import echo
from pydub import AudioSegment

def join_audiofiles_ffmpeg(audiofiles, targetfile):
    """
    Join multiple audio files into a single audio file using a direct call to ffmpeg.

    Arguments:
        audiofiles {list} -- list of audio filenames to join together
        targetfile {str} -- name of file to create from joined audio files

    Returns:
        {bool} -- True if successful, False if not
    """

    cmd = 'ffmpeg -i "concat:{}" -acodec copy "{}"'.format(audiofiles.join('|'), targetfile)
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
