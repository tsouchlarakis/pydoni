class Audio(object):
    """Operate on an audio file"""
    def __init__(self, fname):
        import os
        self.fname = fname
        self.fmt = os.path.splitext(self.fname)[1].replace('.', '').lower()
    def convert(self, dest_fmt):
        """Convert an audio file to destination format and write with identical filename"""
        from pydub import AudioSegment
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
    def split(self, segment_time=60):
        """Split audio file into segments of given length"""
        import os, re
        from pydoni.sh import syscmd
        from pydoni.os import listfiles
        # dirname = os.path.dirname(self.fname)
        cmd = 'ffmpeg -i "{}" -f segment -segment_time {} -c copy "{}-ffmpeg-%03d{}"'.format(
            self.fname, segment_time,
            os.path.splitext(self.fname)[0],
            os.path.splitext(self.fname)[1])
        res = syscmd(cmd)
        # out_pattern = os.path.splitext(self.fname)[0] + '-' + r'\d{3}' + os.path.splitext(self.fname)[1]
        # out_pattern = os.path.basename(out_pattern)
        # files_written = [f for f in os.listdir(dirname) if re.search(out_pattern, f)]
        # return [os.path.join(dirname, f) for f in files_written]
        self.fnames_split = listfiles(pattern=r'ffmpeg-\d{3}\.%s' % self.fmt)
        return None
    def join(self, audiofiles, silence_between=1000):
        """Join multiple audio files into a single file and return the output filename
        audiofiles: list of filenames to concatenate
        silence_between: amount of silence to insert between clips in miliseconds"""
        import os, re
        from pydub import AudioSegment
        from pydoni.pyobj import systime
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
    def set_google_credentials(google_application_credentials_json):
        import os
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_application_credentials_json
    def transcribe(self):
        """Transcribe the given audio file"""
        import re
        from google.cloud import speech_v1p1beta1 as speech
        # Convert audio file to wav if mp3
        if self.fmt == 'mp3':
            self.convert('wav')
        # Split audio file into segments if longer than 60 seconds
        if self.get_duration() > 60:
            self.split(60)
        fnames_transcribe = self.fnames_split if hasattr(self, 'fnames_split') else [self.fname]
        client = speech.SpeechClient()
        transcript = []
        for fname in fnames_transcribe:
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
        transcript = re.sub(r' +', ' ', ' '.join(transcript)).strip()
        self.transcript = transcript
        return transcript
    def get_duration(self):
        import wave
        import contextlib
        with contextlib.closing(wave.open(self.fname,'r')) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            duration = frames / float(rate)
        self.duration = duration
        return duration