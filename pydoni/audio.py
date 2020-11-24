import pydoni
import pydoni.opsys
import pydoni.web


class Audio:
    """
    Operate on an audio file.

    :param audiofile: path to audio file
    :type audiofile: str
    """

    def __init__(self, audiofile):

        import os

        self.logger = pydoni.logger_setup(
            name=pydoni.what_is_my_name(classname=self.__class__.__name__, with_modname=True),
            level=pydoni.modloglev)

        self.audiofile = audiofile
        self.ext = os.path.splitext(self.audiofile)[1]
        self.sound = None
        self.duration = None

        self.logger.logvars(locals())

    def audio_segment(self):
        """
        Wrapper for `pydub.AudioSegment_from*()`. Create an audio file segment from local file.
        """
        import os
        from pydub import AudioSegment

        if self.ext.lower() == '.mp3':
            self.sound = AudioSegment.from_mp3(self.audiofile)
        elif self.ext.lower() == '.wav':
            self.sound = AudioSegment.from_wav(self.audiofile)
        else:
            self.sound = AudioSegment.from_file(self.audiofile)

        try:
            if self.ext.lower() != '.wav':
                self.convert(dest_fmt='wav')
                self.duration = get_duration(os.path.splitext(self.audiofile)[0] + '.wav')
            else:
                self.duration = self.get_duration()

            self.logger.logvars(locals())

        except Exception as e:
            self.logger.exception(e)
            self.logger.error('Unable to get audio duration!')

    def split(self, segment_time):
        """
        Wrapper for pydoni.audio.split_audiofile().

        :param segment_time: time to split audiofile at (in seconds)
        :type segment_time: int
        :return: list of split filenames
        :rtype: list
        """
        self.logger.logvars(locals())
        return pydoni.audio.split_audiofile(self.audiofile, segment_time)

    def get_duration(self):
        """
        Wrapper for pydoni.audio.get_duration().

        :return: duration of audiofile in seconds
        :rtype: float
        """
        self.logger.logvars(locals())
        return pydoni.audio.get_duration(self.audiofile)

    def compress(self, outfile=None):
        """
        Export audio file at low bitrate (92kbps) as an mp3.

        :param audiofile: path to audiofile to compress
        :type audiofile: str
        :param outfile: path to output file to write. If None, replace `audiofile` on disk
        :type outfile: str
        """
        import os

        wavfile = os.path.splitext(self.audiofile)[0] + '.wav'
        if outfile is None:
            outfile = os.path.splitext(self.audiofile)[0] + '.mp3'

        self.sound.export(outfile, bitrate='32k')

        if os.path.isfile(wavfile):
            os.remove(wavfile)

        self.logger.logvars(locals())

    def set_channels(self, num_channels):
        """
        Wrapper for pydub.AudioSegment.set_channels().

        :param num_channels: number of channels to convert audio segment to using `pydub.AudioSegment.set_channels()`
        :type num_channels: int
        """
        self.logger.logvars(locals())
        self.sound = self.sound.set_channels(num_channels)

    def convert(self, dest_fmt, num_channels=None):
        """
        Convert an audio file to destination format and write with identical filename with `pydub`.

        :param dest_fmt: desired output format, one of ['mp3', 'wav']
        :type dest_fmt: str
        :param update_self: set `self.fname` and `self.ext` to converted file and file format after conversion
        :type update_self: bool
        :param num_channels: number of channels to convert audio segment to using `pydub.AudioSegment.set_channels()`
        :type num_channels: int
        """
        import os

        self.logger.logvars(locals())

        dest_fmt = dest_fmt.replace('.', '')
        assert dest_fmt in ['mp3', 'wav']
        assert self.ext != dest_fmt

        outfile = os.path.splitext(self.audiofile)[0] + '.' + dest_fmt
        assert not os.path.isfile(outfile)

        if num_channels is not None:
            if isinstance(num_channels, int):
                self.set_channels(num_channels)

        self.sound.export(outfile, format=dest_fmt)

    def transcribe(self, method='gcs', gcs_split_threshold=55, apply_correction=True, verbose=True):
        """
        Wrapper for `pydoni.audio.transcribe()`.
        Transcribe audio file in .wav format using method of choice.

        :param audiofile: audio file to transcribe
        :type audiofile: str
        :param method: transcription method, as of 2019-12-20 12:24:54 only 'gcs' is supported
        :type method: str
        :param gcs_split_threshold: maximum audio clip size in seconds, if clip exceeds this length it will be split using
        :type gcs_split_threshold: intclass method `split()`
        :param apply_correction: if True, call apply_transcription_corrections() after transcript created
        :type apply_correction: bool
        :param progress: print tqdm progress bar
        :type progress: bool
        :return: transcription string
        :rtype: str
        """

        self.logger.logvars(locals())

        return pydoni.audio.transcribe(
            audiofile=self.audiofile,
            gcs_split_threshold=gcs_split_threshold,
            apply_correction=apply_correction)


class Song(object):
    """
    Gather metadata attributes of an .mp3 file

    :param fname: path to .mp3 file
    :type fname: str
    """

    def __init__(self, fname):

        import os
        import re

        self.logger = pydoni.logger_setup(
            name=pydoni.what_is_my_name(classname=self.__class__.__name__, with_modname=True),
            level=pydoni.modloglev)

        # File parameters
        self.fname = fname
        self.dname = os.path.dirname(os.path.abspath(self.fname))

        # Regex strings used in parsing title, album and/or track index from filename
        self.fname_rgx = r'^(\d+)\s*(.*?)\s*-\s*(.*?)(\.mp3)$'  # "01 Elvis Presley - Hound Dog.mp3"
        self.fname_rgx2 = r'^(\d+)\s*-?\s*(.*?)(\.mp3)$' # "01 - Hound Dog.mp3" OR "01 Hound Dog.mp3"

        # Run `exiftool` on music file
        self.exif = pydoni.sh.EXIF(fname).extract()

        # Extract song-specific data
        self.title     = self.__get_song_title__()
        self.image     = self.__get_song_image__()
        self.track_raw = self.__get_song_track_raw__()
        self.track_idx = self.__get_song_track_idx__(self.track_raw)
        self.disc_raw  = self.__get_song_disc_raw__()
        self.disc_idx  = self.__get_song_disc_idx__(self.disc_raw)
        self.has_image = True if self.image is not None else False

        # Extract album-wide data
        self.artist = self.__get_song_artist__()
        self.album  = self.__get_song_album__()
        self.genre  = self.__get_song_genre__()
        self.year   = self.__get_song_year__()

        # Variables to access in this instance
        self.exitcodemap =  {
            0: 'Metadata successfully written',
            1: 'Ideal value does not exist, no change written',
            2: 'Ideal and current values are the same, no change written'
        }


    def __get_song_image__(self):
        """
        Get the image EXIF metadata.
        :return: str
        """
        if 'picture' in self.exif.keys():
            return self.exif['picture']
        else:
            return None

    def __get_song_disc_raw__(self):
        """
        Get the raw disc EXIF metadata if it exists. Most likely it will not exist.
        :return: str
        """

        if 'part_of_set' in self.exif.keys():
            return self.exif['part_of_set']
        else:
            return None

    def __get_song_disc_idx__(self, disc_raw):
        """
        Return the disc that a song appears in an album. Will generally be 1, but double and
        triple albums should be parsed as 2 and 3, respectively. Try to parse this from the
        filename, if the filename is in the format '2-01 Song Title Here.mp3'. In this case,
        the disc would be parsed as '2'. If not present, attempt to parse from directory
        name, as sometimes directory names contain 'CD 1' or 'Disc 2'. If not in either of
        those places, return nothing.

        :return: int
        """

        import re

        if disc_raw is None:
            return 1

        # Check for disc index in exif
        if '/' in disc_raw:
            return disc_raw.split('/')[0]

        # Look for disc index in filename
        disc_rgx = r'(.*)(CD|Disc|Disk)(\b|\_|\s)(\d+)(.*)'
        if re.match(r'^\d-\d+ ', self.fname):
            return int(self.fname.split('-')[0])
        elif re.match(disc_rgx, self.dname):
            return int(re.sub(disc_rgx, r'\4', self.dname, flags=re.IGNORECASE))

        # Assign to default value of 1 if not found in exif of filename
        return 1

    def __get_song_track_raw__(self):
        """
        Get the raw track information in the EXIF metadata. If unavailable, attempt
        to parse from song filename.

        :return: str
        """

        import re

        if 'track' in self.exif.keys():
            # Some track information in EXIF. Get as much as possible. Might be
            # the numerator and denominator (best case), could be just numerator
            track_raw = str(self.exif['track'])
            if track_raw.isdigit():
                return track_raw
            if '/' in track_raw:
                if track_raw.count('/') == 1:
                    num, den = track_raw.split('/')
                    if num.isdigit() and den.isdigit():
                        # track_raw matches \d+/\d+
                        return '{}/{}'.format(num, den)

        rgx_num_den = r'^(\d+)(\.|-| )(\d+)'
        rgx_num = r'^(\d+)'

        m_num_den = re.match(rgx_num_den, self.fname)
        if m_num_den:
            # Numerator and denominator match. Something like '1-01 Houng Dog.mp3'
            num = m_num_den.group(1)
            den = m_num_den.group(3)
            return '{}/{}'.format(num, den)

        m_num = re.match(rgx_num, self.fname)
        if m_num:
            return m_num.group(1)

        return None

    def __get_song_track_idx__(self, track_raw):
        """
        Return the track index given the raw track metadata. Format will generally be a
        single digit, or two digits, separated by a forward slash. Ex: '5', '9', '2/12'.
        Extract the 5, 9 and 2 respectively and convert to int.

        :return: int or None
        """
        if track_raw is None:
            return None

        if '/' in track_raw:
            if track_raw.count('/') == 1:
                num = track_raw.split('/')[0]
                if num.isdigit():
                    return int(num)

        if track_raw.isdigit():
            return int(track_raw)

        return None

    def __get_song_year__(self):
        """
        Parse the year from the directory (album) name.
        :return: int or None
        """

        import re

        if re.match(r'(.*?)\((\d{4})\)', self.dname):
            year = re.sub(r'(.*?)(\(\[)(\d{4})(\)\])(.*)', r'\3', self.dname)
            year = int(year) if year.isdigit() else None
            return year

        elif re.match(r'^\d{4}', self.dname):
            year = re.sub(r'^(\d{4})(.*)', r'\1', self.dname)
            year = int(year) if year.isdigit() else None
            return year

        else:
            return None

    def __get_song_title__(self):
        """
        Attempt to parse song title from raw filename.
        :return: str or None
        """

        import re
        from titlecase import titlecase

        # First check regex, then filename
        if 'title' in self.exif.keys():
            val = self.exif['title']
        elif re.match(self.fname_rgx, self.fname):
            val = re.sub(self.fname_rgx, r'\3', self.fname).strip()
        elif re.match(self.fname_rgx2, self.fname):
            val = re.sub(self.fname_rgx, r'\2', self.fname).strip()
        else:
            val = None

        # Clean title
        if val is not None:
            val = self.__generic_clean__(val)
            val = re.sub(r'(\w)(\/)(\w)', r'\1 \2 \3', val)
            return titlecase(val)
        else:
            return val

    def __get_song_artist__(self):
        """
        Attempt to parse song artist from raw filename.
        :return: str or None
        """

        import re
        from titlecase import titlecase

        # First check EXIF metadata
        if 'artist' in self.exif.keys():
            val = self.exif['artist']
        elif re.match(self.fname_rgx, self.fname):
            val = re.sub(self.fname_rgx, r'\2', self.fname).strip()
        else:
            val = None

        if val is not None:
            if isinstance(val, str):
                if val > '':
                    val = self.__generic_clean__(val)
                    val = re.sub(r'(\w)( ?\/)(\w)', r'\1, \3', val)  # Replace slash with comma
                    return titlecase(val)
                else:
                    val = None

        return val

    def __get_song_album__(self):
        """
        Get EXIF album value and apply any corrections.
        :return: str
        """
        import os
        import re

        if 'album' in self.exif.keys():
            val = self.exif['album']
            val = self.__generic_clean__(val)
            val = re.sub(r'(\w)(\/)(\w)', r'\1 \2 \3', val)
            val = val.replace('the', 'The')
            val = re.sub(r'^( *)(\[?)(\d{4})(\]?)( *)(-?|\.?)(.*)$', r'\7', val).strip()
            return val

        else:
            # No album attribute somehow, just assume directory name
            return os.path.dirname(self.dname)

    def __get_song_genre__(self):
        """
        Get song genre from EXIF metadata
        :return: str
        """
        if 'genre' in self.exif.keys():
            val = self.exif['genre']
            val = self.__generic_clean__(val)
            val = val.replace('/', ', ')
            return val
        else:
            return None

    def __generic_clean__(self, val):
        """
        Apply general cleaning methods to any of the EXIF metadata attributes: artist,
        title, album, genre.

        :param val: value to clean
        :type val: str
        :return: str
        """

        import re
        from titlecase import titlecase

        # Keep words that are all uppercase, generally acronyms. Titlecase will
        # convert all letters besides the first to lowercase
        keep_capital = [i for i, item in enumerate(val.split(' ')) if \
                        item == item.upper() and re.match('[A-Z]+', item)]
        x = titlecase(val).split()  # Apply titlecase, then...
        if len(keep_capital):  # Keep words that are all capital that will be mutated by titlecase
            for idx in keep_capital:
                x[idx] = val.split(' ')[idx]

        # Make substitutions that have to do with common tags on the filenames of songs
        # These include "Bonus Track", "Remastered", "Alt Version", etc.
        # Replace so that these tags are enclosed in square brackets [] instead of
        # parenthesis () as they generally are.
        x = ' '.join(item for item in x)

        # Regex replace (case insensitive)
        rgx_replacements = [
            (r'\] \[', ']['),
            (r' +', ' '),
            (r'\((Alternative|Alternate|Bonus) (Take|Track|Song)\)', '[#]'),
            (r'\((Alternative|Alt|Version|ft|feat|featuring|with|Soundtrack|Remastered|Remaster|Remasterd|Remix|Unreleased)(.*)\)', r'[\1\2]'),
            (r'\((.*?)(Alternative|Alt|Version|Unreleased)\)', r'[\1\2]'),
            (r'\((\d{4}) (Remaster|Remastered|Remastrd|Remix)\)', r'[\1 \2]'),
            (r'\((Remaster|Remastered|Remix) (\d{4})\)', r'\[\2 \1\]'),
            (r'\(Live\)', '[Live]')
        ]
        for rgx, repl in rgx_replacements:
            x = re.sub(rgx, repl, x, flags=re.IGNORECASE)

        # General string cleaning primarily for song titles
        replacements = [
            ('(#)', '[#]'),
            ('(*)', '[#]'),
            ('[*]', '[#]'),
            ("O'Er", "O'er"),
            ("'N'", "'n'"),
            ('[Ft', '[ft.'),
            ('[Ft.', '[ft.'),
            ('[Feat', '[ft.'),
            ('[Feat.', '[ft.'),
            ('[Featuring', '[ft.'),
            ('[Featuring.', '[ft.'),
            ('W / ', 'w/'),
            ('.mp3', ''),
            ('_', ' ')
        ]
        for string, repl in replacements:
            x = x.replace(string, repl)

        return x

    def set_exif(self, attr_name, attr_value):
        """
        Set song metadata field using mid3v2.

        :param attr_name: name of attribute to set, must be one of ['artist', 'album', 'song',
                          'comment', 'picture', 'genre', 'year', 'date', 'track']
        :type attr_name: str
        :param attr_value: value of attribute to set
        :type attr_value: any
        :return: bool or: True if successful
        :type or: str
        """

        pydoni.sh.mid3v2(self.fname, attr_name=attr_name, attr_value=attr_value)
        return True


class Album(object):
    """
    An Album datatype that will retrieve the relevant metadata attributes of an album by
    considering the metadata of all songs within the album.

    :param dpath: path to directory containing album of music files
    :type dpath: str
    :param valid_ext: list of valid music file extensions
    :type valid_ext: list
    """

    def __init__(self, dpath, valid_ext=['.mp3', '.flac']):

        import os
        import re
        from titlecase import titlecase

        self.logger = pydoni.logger_setup(
            name=pydoni.what_is_my_name(classname=self.__class__.__name__, with_modname=True),
            level=pydoni.modloglev)

        os.chdir(dpath)

        self.dname = os.path.basename(dpath)
        self.fnames = pydoni.opsys.listfiles(ext=valid_ext)

        assert len(self.fnames)

        # Loop over each song file and get album attributes:
        # album artist, album title, album year, album genre, number of tracks on disc
        albuminfo = dict(
            artist=[],
            title=[],
            year=[],
            genre=[],
            songs=[],
            has_image=[]
        )
        songinfo = dict(
            title=[],
            song_disc_idxs=[],
            song_class_instances=[]
        )
        track_raw_vals = []
        for fname in self.fnames:
            song = Song(fname)
            albuminfo['artist'].append(song.artist)
            albuminfo['title'].append(song.album)
            albuminfo['year'].append(song.year)
            albuminfo['genre'].append(song.genre)
            albuminfo['has_image'].append(song.has_image)
            songinfo['title'].append(song.title)
            songinfo['song_disc_idxs'].append(song.disc_idx)
            songinfo['song_class_instances'].append(song)
            track_raw_vals.append(song.track_raw)

            # Get number of discs in album
            self.disc_count = self.__get_discs_in_album__(
                songinfo['song_disc_idxs'])

            # Get number of tracks on disc
            self.track_total = self.__get_tracks_on_disc__(track_raw_vals)

            # Now condense all album attributes!

            # If multiple artists found in album, assume compilation album, and do
            # not alter artist
            if len(list(set(albuminfo['artist']))) == 1:
                self.artist = pydoni.listmode(albuminfo['artist'])
            else:
                self.artist = albuminfo['artist']

            # Get most frequently-occurring year, genre and album title
            self.year  = pydoni.listmode(albuminfo['year'])
            self.genre = pydoni.listmode(albuminfo['genre'])
            self.title = pydoni.listmode(albuminfo['title'])

            # If any songs have an image, set image indicator to True
            self.has_image = True if any(albuminfo['has_image']) else False

            # Set song-level information
            self.songs = songinfo['title']
            self.song_class_instances = songinfo['song_class_instances']

            # If any album attributes are None, attempt to correct using any means necessary
            if self.year is None:
                self.year = self.__get_year_from_dname__()

    def __get_discs_in_album__(self, song_disc_idxs):
        """
        Get the number of discs in album.
        :return: int
        """
        import re

        # Get first from song disc indices
        discs = list(filter(None, list(set(song_disc_idxs))))
        discs = [x for x in discs if isinstance(x, int)]
        if len(discs) > 0:
            # There is disc information
            return max(discs)
        else:
            # No disc information from song disc indices, attempt to parse from filenames
            # of all files in album, then from directory name
            discs = []
            disc_dname_rgx = r'(.*)(CD|Disc|Disk)(\b|\_|\s)(\d+)(.*)'
            for fname in self.fnames:
                if re.match(r'^\d-\d+ ', fname):
                    # Filename matches for example '1-05 Test Song Name.mp3'. In this
                    # case, we want to extract the '1'.
                    return int(fname.split('-')[0])
                elif re.match(disc_dname_rgx, self.dname):
                    return int(re.sub(disc_dname_rgx, r'\4', self.dname, flags=re.IGNORECASE))
                else:
                    return 1

    def __get_tracks_on_disc__(self, track_raw_vals):
        """
        Return the total number of tracks in album. First check song raw track index
        metadata for total number of tracks. If not present, assume the total number
        of tracks on disc is equal to the total number of music files in directory.

        :param trackraw_vals: list of trackraw values
        :type trackraw_vals: list
        :return: int
        """
        if all([x is None for x in track_raw_vals]):
            return None

        track_denoms = []
        for x in track_raw_vals:
            if isinstance(x, str):
                if '/' in x:
                    track_denoms.append(x.split('/')[1])
        track_denoms = list(set(track_denoms))

        if len(track_denoms) == 1:
            track_total = track_denoms[0]
            if track_total.isdigit():
                return int(track_total)
            else:
                return len(self.fnames)

        elif len(track_denoms) > 1:
            # Multiple track denominators -> album has multiple tracks. Get the total
            # number of song files in directory
            return len(self.fnames)

        else:
            # 0 for denominator. Default to total number of song files in directory
            return len(self.fnames)

    def __get_year_from_dname__(self):
        """
        Attempt to extract album year from directory name.
        :return: int or None
        """
        import os
        import re
        from datetime import datetime

        # Establish valid year ranges to check extracted year string against, from year
        # 1800 to current year plus one year
        valid_years = range(1800, int(datetime.now().strftime('%Y')) + 1)

        # First check first four characters of directory name for year. Often times
        # directory names will be in the format "YYYY ALBUM_TITLE"
        val = os.path.basename(self.dname)
        x = val[0:4]
        if x.isdigit():
            x = int(x)
            if x in valid_years:
                return x

        # Then check for year in parentheses or square brackets
        years = re.findall(r'\(\d{4}\)', val) + re.findall(r'\[\d{4}\]', val)
        if len(years):
            for x in years:
                x = re.sub(r'\(|\)|\[|\]', '', x)
                if x.isdigit():
                    x = int(x)
                    if x in valid_years:
                        return x

        # Then check in the entire directory name for four digits matching a valid year
        years = re.findall(r'\d{4}', val)
        if len(years):
            for x in years:
                if x.isdigit():
                    x = int(x)
                    if x in valid_years:
                        return x

        # If year still cannot be found, return None
        return None


    def scrape_wikipedia_genre(self, get_genre=True, get_image=True, image_outfile=None):
        """
        Find Wikipedia song link from Google to scrape for genre. If song page cannot
        be found or does not exist on Wikipedia, use the album's Wikipedia page. If that
        doesn't exist and genre is still unable to be found, return original genre. Also
        scrape image from same Wikipedia page.

        :param get_genre: if True, attempt to retrieve Wikipedia album genre
        :type get_genre: bool
        :param image_outfile: path to desired image outfile from Wikipedia
        :type image_outfile: str
        :return: genre string scraped from Wikipedia, may be comma-separated for multiple genres
        :rtype: str
        """
        import requests
        import os
        from send2trash import send2trash

        def search_google_for_album_wikipage(artist, year, album):
            """
            Search Wikipedia for album URL.

            :param artist: album artist
            :type artist: str
            :param album: album title
            :type album: str
            :return: URL to Wikipedia page
            :rtype: str
            """
            import googlesearch
            import re

            clean_album = re.sub(
                r'(\[|\()(.*?)(\]|\))|CD\s*\d+|Disc\s*\d+', '', album, flags=re.IGNORECASE).strip()
            query = '{} {} {} album site:wikipedia.org'.format(
                artist, year if year is not None else '', clean_album)
            query = query.replace('  ', ' ')
            wikilink = list(googlesearch.search(
                query, tld='com', num=1, stop=1, pause=2))
            if len(wikilink):
                return wikilink[0]
            else:
                return None

        def extract_genre_from_wikipage(wikilink):
            """
            Parse Wikipedia page HTML for album genre.

            :param wikilink: link to Wikipedia page to scrape and
            :type wikilink: str
            :return: genre(s) parsed from Wikipedia page
            :rtype: str
            """
            import re
            from titlecase import titlecase

            # Scrape page for CSS selector
            genre = pydoni.web.get_element_by_selector(wikilink, '.category a')
            genre = [genre] if isinstance(genre, str) else genre
            if not len(genre):
                return None

            # Parse multiple genres if present
            genre = [x for x in genre if not re.search(r'\[\d+\]', x)]
            if not len(genre):
                return None

            # Capitalize text for each genre returned
            genre = titlecase(', '.join(x for x in genre))
            return genre

        def extract_image_from_wikipage(wikilink, image_outfile, overwrite=True):
            """
            Parse Wikipedia page HTML for album image.

            :param wikilink: link to Wikipedia page to scrape
            :type wikilink: str
            :param overwrite: if True, overwrite `outfile` if it exists
            :type overwrite: bool

            :return:
            """
            import os
            import re

            # Get image xpath
            img_xpath = pydoni.web.get_element_by_xpath(
                wikilink, xpath='//*[contains(concat( " ", @class, " " ), concat( " ", "image", " " ))]//img/@src')
            if img_xpath is None or not len(img_xpath):
                return None
            else:
                img_xpath = img_xpath[0]

            # Extract image link from image xpath
            img_xpath = re.sub(r'thumb\/', '', img_xpath)
            img_xpath = re.sub(r'(.*?)(\.(jpg|jpeg|png)).*', r'\1\2', img_xpath)
            img_url = re.sub(r'^\/\/', 'https://', img_xpath)

            # Download image file to `outfile`
            outfile = os.path.splitext(image_outfile)[0] + os.path.splitext(img_url)[len(os.path.splitext(img_url))-1]
            if not os.path.isfile(outfile) or overwrite:
                pydoni.web.downloadfile(img_url, outfile)

            return outfile

        def verify_downloaded_image(album_artwork_file):
                """
                Check if downloaded file is >1kb. Sometimes an image will be downloaded that is not
                a real image file.

                :param album_artwork_file: downloaded image file
                :type album_artwork_file: str
                :return: bool
                """
                try:
                    if os.path.isfile(album_artwork_file):
                        return int(stat(album_artwork_file)['Size']) > 1000
                    else:
                        return False
                except:
                    return False

        # Execute steps used for getting both Genre and Image
        # Get wikipedia link
        wikilink = search_google_for_album_wikipage(
            self.artist, self.year, self.title)

        # Get Wikipedia link if possible and overwrite `self.genre` if scraping successful
        if get_genre:
            if isinstance(wikilink, str):
                if requests.get(wikilink).status_code == 200:  # Webpage exists
                    try:
                        parsed_genre = extract_genre_from_wikipage(wikilink)
                        if parsed_genre is not None:
                            # Overwrite genre
                            self.genre = parsed_genre
                            self.is_genre_from_wikipedia = True
                        else:
                            self.is_genre_from_wikipedia = False
                    except:
                        # Scraping fails, do not overwrite genre
                        self.is_genre_from_wikipedia = False

        if get_image:
            # Get image by scraping Wikipedia page
            if isinstance(wikilink, str):
                downloaded_file = extract_image_from_wikipage(wikilink, image_outfile)
                if isinstance(downloaded_file, str):
                    if os.path.isfile(downloaded_file):
                        # Check that image is valid
                        if not verify_downloaded_image(downloaded_file):
                            if os.path.isfile(downloaded_file):
                                send2trash(downloaded_file)
                            else:
                                self.is_image_downloaded_from_wikipedia = False
                        else:
                            self.is_image_downloaded_from_wikipedia = True
                    else:
                        self.is_image_downloaded_from_wikipedia = False
                else:
                    self.is_image_downloaded_from_wikipedia = False
            else:
                self.is_image_downloaded_from_wikipedia = False


def transcribe(
        audiofile,
        method='gcs',
        gcs_split_threshold=50,
        apply_correction=True,
        progress=False):
    """
    Transcribe audio file in .wav format using method of choice.

    :param audiofile: audio file to transcribe
    :type audiofile: str
    :param method: transcription method, as of 2019-12-20 12:24:54 only 'gcs' is supported
    :type method: str
    :param gcs_split_threshold: maximum audio clip size in seconds, if clip exceeds this length it will be split using
    :type gcs_split_threshold: intclass method `split()`
    :param apply_correction: if True, call apply_transcription_corrections() after transcript created
    :type apply_correction: bool
    :param progress print tqdm progress bar
    :return: transcription string
    :rtype: str
    """
    import numpy as np
    import re
    import os
    from google.cloud import speech_v1p1beta1
    from tqdm import tqdm

    assert method in ['gcs']

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)

    # Copy `audiofile` to temporary program environment
    wd = os.path.join(os.path.expanduser('~'), '.tmp.pydoni.transcribe')
    logger.info("Creating temporary environment at '%s'" % wd)
    env = pydoni.classes.ProgramEnv(wd, overwrite=True)

    logger.info("Copying file '%s' to environment" % audiofile)
    env.copyfile(audiofile, set_focus=True)

    try:
        if method == 'gcs':

            if 'GOOGLE_APPLICATION_CREDENTIALS' not in os.environ.keys():
                errmsg = "Must run 'set_google_credentials()' before running" \
                "GCS transcription!"
                logger.error(errmsg)
                raise Exception(errmsg)

            # Ensure file is in mono .wav format. If not, create a temporary
            # .wav file
            logger.info('Checking file extension')
            ext = os.path.splitext(env.focus)[1]
            if ext.lower() != '.wav':
                logger.warn('Converting file to mono WAV format')
            else:
                logger.info('Converting file to mono WAV format')

            # Execute file format conversion
            try:
                fname = os.path.splitext(env.focus)[0] + '.wav'
                audio = Audio(env.focus)
                audio.set_channels(1)
                audio.sound.export(fname, format='wav')
                env.focus = fname
            except Exception as e:
                logger.exception('Failed to convert file to mono wav format')
                raise e

            # Split audio file into segments if longer than
            # `gcs_split_threshold` seconds
            duration = get_duration(env.focus)
            logger.info('Audio duration detected: %s seconds' % str(duration))

            if np.floor(duration) > gcs_split_threshold:
                logger.info('Splitting audio into %s second chunks' % \
                    gcs_split_threshold)
                fnames = split_audiofile(
                    audiofile=env.focus,
                    segment_time=gcs_split_threshold)
            else:
                fnames = [env.focus]

            # Set up transcription
            logger.info('Initializing transcription engine')
            transcript = []
            client = speech.SpeechClient()

            # Loop over files to transcribe and apply Google Cloud transcription
            logger.info('Transcribing audio')
            if progress:
                pbar = tqdm(total=len(fnames), unit='audiofile')

            for fname in fnames:
                logger.info("Transcribing file '%s'" % fname)

                try:
                    with open(fname, 'rb') as audio_file:
                        content = audio_file.read()
                        aud = speech.types.RecognitionAudio(content=content)
                        config = speech.types.RecognitionConfig(
                            encoding=speech.enums.RecognitionConfig.AudioEncoding.LINEAR16,
                            # sample_rate_hertz=400,
                            language_code='en-US',
                            audio_channel_count=1,
                            enable_separate_recognition_per_channel=False)
                        response = client.recognize(config, aud)

                    # Each result is for a consecutive portion of the audio.
                    # Iterate through them to get the transcripts for the
                    # entire audio file.
                    for result in response.results:
                        # The first alternative is the most likely one for
                        # this portion.
                        transcript.append(result.alternatives[0].transcript)

                    if progress:
                        pbar.update(1)

                except Exception as e:
                    logger.exception("Failed to transcribe file '%s'" % fname)
                    env.delete_env()
                    logger.warn('Temporary program environment deleted')
                    raise e

            if progress:
                pbar.close()

            # De-capitalize first letter of each transcript. This happens as a long audio segment is
            # broken into smaller clips, the first word in each of those clips becomes capitalized.
            if 'transcript' in locals():
                if isinstance(transcript, list):
                    transcript = [x[0].lower() + x[1:] for x in transcript]
                    transcript = re.sub(r' +', ' ', ' '.join(transcript)).strip()

                    # Apply transcription corrections if specified
                    if apply_correction:
                        logger.info('Applying transcription corrections')
                        transcript = apply_transcription_corrections(transcript)
                    else:
                        logger.warn('NOT applying transcription corrections')

                else:
                    logger.error('`transcript` variable not of type list!')
                    logger.debug('`transcript` value: %s' % transcript)
                    logger.debug('`transcript` dtype: %s' % type(transcript))
                    env.delete_env()
                    logger.warn('Temporary program environment deleted')
            else:
                logger.error('Unknown error: `transcript` variable not in `locals()`!')
                env.delete_env()
                logger.warn('Temporary program environment deleted')

    except Exception as e:
        logger.exception('Transcription failed!')
        env.delete_env()
        logger.warn('Temporary program environment deleted')
        raise e

    env.delete_env()

    return transcript


def apply_transcription_corrections(transcript):
    """
    Apply any and all corrections to output of transcribe().

    :param transcript: transcript string to apply corrections to
    :type transcript: str
    :return: transcript string with corrections
    :rtype: str
    """

    def smart_dictation(transcript):
        """
        Apply corrections to spoken keywords like 'comma', 'period' or 'quote'/'unquote'.

        :param transcript: transcript string
        :type transcript: str
        :return: transcript string
        :rtype: str
        """
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
        """
        Capitalize transcript intelligently according to the following methods:
            1. Capitalize first letter of each sentence, split by newline character.
            2. Capitalize word following keyphrase 'make capital'.
            3. Capitalize word and concatenate letters following keyphrase 'make letter'.
            4. Capitalie letter following '?'.

        :param transcript: transcript string
        :type transcript: str
        :return: transcript string
        :rtype: str
        """
        import re

        # Capitalize first letter of each sentence, split by newline character
        val = transcript
        val = '\n'.join([pydoni.cap_nth_char(x, 0) for x in val.split('\n')])

        # Capitalize word following keyphrase 'make capital'
        cap_idx = [m.start()+len('make capital')+1 for m in re.finditer('make capital', val)]
        if len(cap_idx):
            for idx in cap_idx:
                val = pydoni.cap_nth_char(val, idx)
            val = val.replace('make capital ', '')

        # Capitalize and concatenate letters following keyphrase 'make letter'. Ex: 'make letter a' -> 'A'
        letter_idx = [m.start() + len('make letter') + 1 for m in re.finditer('make letter', val)]
        if len(letter_idx):
            for idx in letter_idx:
                val = pydoni.cap_nth_char(val, idx)
                val = pydoni.replace_nth_char(val, idx+1, '.')
                if idx == letter_idx[len(letter_idx)-1]:
                    val = pydoni.insert_nth_char(val, idx+2, ' ')
            val = val.replace('make letter ', '')

        # Capitalize letter following '?'
        if '? ' in val:
            q_idx = [m.start() + len('? ') for m in re.finditer(r'\? ', val)]
            for idx in q_idx:
                val = pydoni.cap_nth_char(val, idx)
        return val

    def excess_spaces(transcript):
        """
        Replace extra spaces with a single space.

        :param transcript: transcript string
        :type transcript: str
        :return: transcript string
        :rtype: str
        """
        import re
        return re.sub(r' +', ' ', transcript)

    def manual_corrections(transcript):
        """
        Apply manual corrections to transcription.

        :param transcript: transcript string
        :type transcript: str
        :return: transcript string
        :rtype: str
        """
        import re

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

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)

    # Apply all correction methods
    transcript = smart_dictation(transcript)
    transcript = smart_capitalize(transcript)
    transcript = excess_spaces(transcript)
    transcript = manual_corrections(transcript)
    logger.info('Applied transcription corrections')

    return transcript


def join_audiofiles_pydub(audiofiles, targetfile, silence_between):
    """
    Join multiple audio files into a single audio file using pydub.

    :param audiofiles: list of audio filenames to join together
    :type audiofiles: list
    :param silence_between: milliseconds of silence to insert between clips
    :type silence_between: int
    """
    import os
    from pydub import AudioSegment

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)

    for file in audiofiles:
        ext = os.path.splitext(file)[1].lower()
        assert ext in ['.mp3', '.wav']

    logger.logvars(locals())

    # Create sound object, initialize with 1ms of silence
    sound = AudioSegment.silent(duration=1)
    logger.info('Created Pydub sound object')

    # Iterate over list of audio files and join audio
    for file in audiofiles:
        ext = os.path.splitext(file)[1].lower()

        if ext.lower() == '.mp3':
            fnamesound = AudioSegment.from_mp3(file)
        else:
            fnamesound = AudioSegment.from_wav(file)

        sound = sound + fnamesound

        if silence_between > 0:
            sound = sound + AudioSegment.silent(duration=silence_between)

        logger.info("Appended sound file '%s'" % file)

    sound.export(targetfile, format='mp3')
    logger.info("Exported '%s'" % targetfile)


def join_audiofiles(audiofiles, targetfile, method=None, silence_between=0):
    """
    Join multiple audio files into a single audio file.

    :param audiofiles: list of audio filenames to join together
    :type audiofiles: list
    :param targetfile: name of file to create from joined audio files
    :type targetfile: str
    :param method: method to join audiofiles, one of ['ffmpeg', 'pydub']. If None, method is automatically
    :type method: strdetermined
    :param silence_between: milliseconds of silence to insert between clips
    :type silence_between: int
    """
    import os

    assert isinstance(silence_between, int)
    assert isinstance(audiofiles, list)
    assert len(audiofiles) > 1

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    for fname in audiofiles:
        assert os.path.isfile(fname)

    if method is None:
        if silence_between == 0:
            method = 'ffmpeg'
        else:
            method = 'pydub'

    assert method in ['ffmpeg', 'pydub']

    if method == 'ffmpeg':
        pydoni.sh.FFmpeg().join(audiofiles, targetfile)
    else:
        join_audiofiles_pydub(audiofiles, targetfile, silence_between)

    logger.info("Exported '%s'" % targetfile)


def split_audiofile(audiofile, segment_time):
    """
    Split audio file into segments of given length using ffmpeg.
    TODO: Add equal_parts parameter, to split file into 2, 3, ... equal parts

    :param audiofile: path to audio file to split
    :type audiofile: str
    :param segment_time: length of split audio clips in seconds to split audio file into if length is too long
    :type segment_time: int
    :return: list of split filenames
    :rtype: list
    """
    import os

    assert os.path.isfile(audiofile)
    assert isinstance(segment_time, int)

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)

    wd = os.getcwd()

    # Split audio file with FFmpeg
    logger.info('Splitting audiofile with FFmpeg')
    pydoni.sh.FFmpeg().split(audiofile, segment_time=segment_time)

    # Return resulting files under `fnames_split` attribute
    dname = os.path.dirname(audiofile)
    dname = '.' if dname == '' else dname
    os.chdir(dname)
    splitfiles = pydoni.opsys.listfiles(
        path=dname,
        pattern=r'%s-ffmpeg-\d{3}\.%s' % \
            (os.path.basename(os.path.splitext(audiofile)[0]), os.path.splitext(audiofile)[1].replace('.', '')))

    if dname != '.':
        splitfiles = [os.path.join(dname, x) for x in splitfiles]

    logger.info("Split into files: '%s'" % str(splitfiles))
    logger.logvars(locals())

    os.chdir(wd)
    return splitfiles


def get_duration(audiofile):
    """
    Get the duration of a WAV audio file.

    :param audiofile: path to audio file to get duration of
    :type audiofile: str
    :return: duration of audio file in seconds
    :rtype: float
    """
    import contextlib
    import wave
    import os

    assert os.path.splitext(audiofile)[1].lower() == '.wav'

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.info("Getting duration of file '%s'" % audiofile)

    with contextlib.closing(wave.open(audiofile, 'r')) as f:
        logger.info('Successfully opened WAV file')
        frames = f.getnframes()
        logger.info('Determined number of frames: %s' % str(frames))
        rate = f.getframerate()
        logger.info('Determined framerate: %s' % str(rate))
        duration = frames / float(rate)
        logger.info('Determined duration: %s' % str(duration))

    return duration


def set_google_credentials(google_application_credentials_json):
    """
    Set environment variable as path to Google credentials JSON file.

    :param google_application_credentials_json: path to google application credentials file
    :type google_application_credentials_json: str
    """
    import os

    assert(os.path.isfile(google_application_credentials_json))

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_application_credentials_json

    logger.info("Google application credentials set as file '%s'" % \
        google_application_credentials_json)
