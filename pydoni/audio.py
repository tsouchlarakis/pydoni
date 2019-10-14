import contextlib
import numpy as np
import re
import wave
from google.cloud import speech_v1p1beta1 as speech
from os import chdir
from os import environ
from os import getcwd
from os import remove
from os.path import basename
from os.path import dirname
from os.path import expanduser
from os.path import isfile
from os.path import join
from os.path import splitext
from pydub import AudioSegment
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
        if outfile is None:
            outfile = splitext(self.audiofile)[0] + '.mp3'
        wavfile = splitext(self.audiofile)[0] + '.wav'
        self.sound.export(outfile, bitrate='32k')
        if isfile(wavfile):
            remove(wavfile)

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


class Song(object):
    """
    Gather metadata attributes of an .mp3 file

    Arguments:
        fname {str} -- path to .mp3 file
    """
    
    def __init__(self, fname):

        # File parameters
        self.fname = fname
        self.dname = dirname(abspath(self.fname))

        # Regex strings used in parsing title, album and/or track index from filename
        self.fname_rgx = r'^(\d+)\s*(.*?)\s*-\s*(.*?)(\.mp3)$'  # "01 Elvis Presley - Hound Dog.mp3"
        self.fname_rgx2 = r'^(\d+)\s*-?\s*(.*?)(\.mp3)$' # "01 - Hound Dog.mp3" OR "01 Hound Dog.mp3"
        
        # Run `exiftool` on music file
        self.exif = EXIF(fname).run(wrapper='doni')

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
        
        Returns:
            {str}
        """
        if 'picture' in self.exif.keys():
            return self.exif['picture']
        else:
            return None

    def __get_song_disc_raw__(self):
        """
        Get the raw disc EXIF metadata if it exists. Most likely it will not exist.
        
        Returns:
            {str}
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
        
        Returns:
            {int}
        """

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
        
        Returns:
            {str}
        """
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
        
        Returns:
            {int} or {None}
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
        
        Returns:
            {int} or {None}
        """
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
        
        Returns:
            {str} or {None}
        """

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
        
        Returns:
            {str} or {None}
        """

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
        
        Returns:
            {str}
        """

        if 'album' in self.exif.keys():
            val = self.exif['album']
            val = self.__generic_clean__(val)
            val = re.sub(r'(\w)(\/)(\w)', r'\1 \2 \3', val)
            val = val.replace('the', 'The')
            val = re.sub(r'^( *)(\[?)(\d{4})(\]?)( *)(-?|\.?)(.*)$', r'\7', val).strip()
            return val
        
        else:
            # No album attribute somehow, just assume directory name
            return dirname(self.dname)

    def __get_song_genre__(self):
        """
        Get song genre from EXIF metadata
        
        Returns:
            {str}
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
    
        Arguments:
            val {str} -- value to clean
        
        Returns:
            {str}
        """

        # Keep words that are all uppercase, generally acronyms. Titlecase will
        # convert all letters besides the first to lowercase
        keep_capital = [i for i, item in enumerate(val.split(' ')) if
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
        x = re.sub(r'\((Alternative|Alternate|Bonus) (Take|Track|Song)\)',
                   '[#]', x, flags=re.IGNORECASE)
        x = re.sub(r'\((Alternative|Alt|Version|ft|feat|featuring|with|Soundtrack|Remastered|Remaster|Remasterd|Remix|Unreleased)(.*)\)',
                   r'[\1\2]', x, flags=re.IGNORECASE)
        x = re.sub(r'\((.*?)(Alternative|Alt|Version|Unreleased)\)',
                   r'[\1\2]', x, flags=re.IGNORECASE)
        x = re.sub(r'\((\d{4}) (Remaster|Remastered|Remastrd|Remix)\)',
                   r'[\1 \2]', x, flags=re.IGNORECASE)
        x = re.sub(
            r'\((Remaster|Remastered|Remix) (\d{4})\)', r'\[\2 \1\]', x, flags=re.IGNORECASE)
        x = re.sub(r'\(Live\)', '[Live]', x, flags=re.IGNORECASE)
        x = re.sub(r'\] \[', '][', x)

        # General string cleaning primarily for song titles
        x = re.sub(r' +', ' ', x)
        x = x.replace('(#)', '[#]')
        x = x.replace('(*)', '[#]')
        x = x.replace('[*]', '[#]')
        x = x.replace("O'Er", "O'er")
        x = x.replace("'N'", "'n'")
        x = x.replace('[Ft', '[ft.')
        x = x.replace('[Ft.', '[ft.')
        x = x.replace('[Feat', '[ft.')
        x = x.replace('[Feat.', '[ft.')
        x = x.replace('[Featuring', '[ft.')
        x = x.replace('[Featuring.', '[ft.')
        x = x.replace('W / ', 'w/')
        x = x.replace('.mp3', '')
        x = x.replace('_', ' ')

        return x

    def set_exif(self, attr_name, attr_value):
        """
        Set song metadata field using mid3v2.
        
        Arguments:
            attr_name {str} -- name of attribute to set, must be one of ['artist', 'album', 'song', 'comment', 'picture', 'genre', 'year', 'date', 'track']
            attr_value {value} -- value of attribute to set
        
        Returns:
            {bool} or {str} -- True if successful, error message as string if unsuccessful
        """
        
        try:
            mid3v2(self.fname, attr_name=attr_name, attr_value=attr_value)
            return True
        except Exception as e:
            return  str(e)


class Album(object):
    """
    An Album datatype that will retrieve the relevant metadata attributes of an album by
    considering the metadata of all songs within the album.
    
    Arguments:
        dpath {str} -- path to directory containing album of music files
    """

    def __init__(self, dpath, valid_ext=['.mp3', '.flac']):
        chdir(dpath)
        self.dname = basename(dpath)
        self.fnames = listfiles(ext=valid_ext)
        assert len(self.fnames)

        # Loop over each song file and get album attributes:
        # album artist, album title, album year, album genre, number of tracks on disc
        albuminfo = dict(
            artist    = [],
            title     = [],
            year      = [],
            genre     = [],
            songs     = [],
            has_image = []
        )
        songinfo = dict(
            title                = [],
            song_disc_idxs       = [],
            song_class_instances = []
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
                self.artist = listmode(albuminfo['artist'])
            else:
                self.artist = albuminfo['artist']

            # Get most frequently-occurring year, genre and album title
            self.year  = listmode(albuminfo['year'])
            self.genre = listmode(albuminfo['genre'])
            self.title = listmode(albuminfo['title'])

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
        
        Returns:
            {int}
        """

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
    
        Arguments:
            trackraw_vals {list} -- list of trackraw values 
        
        Returns:
            {int}
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

        Returns:
            {int} or {None}
        """

        # Establish valid year ranges to check extracted year string against, from year
        # 1800 to current year plus one year
        valid_years = range(1800, int(datetime.datetime.now().strftime('%Y')) + 1)

        # First check first four characters of directory name for year. Often times
        # directory names will be in the format "YYYY ALBUM_TITLE"
        val = basename(self.dname)
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
        
        Keyword Arguments:
            get_genre {bool} -- if True, attempt to retrieve Wikipedia album genre (default: {True})
            get_image {bool} -- if True, attempt to retrieve Wikipedia album image (default: {True})
            image_outfile {str} -- path to desired image outfile from Wikipedia (default: {None})
        
        Returns:
            {str} -- genre string scraped from Wikipedia, may be comma-separated for multiple genres
        """

        def search_google_for_album_wikipage(artist, year, album):
            """
            Search Wikipedia for album URL.
            
            Arguments:
                artist {str} -- album artist
                year {str} -- album year
                album {str} -- album title
            
            Returns:
                {str} -- URL to Wikipedia page
            """
            clean_album = re.sub(
                r'(\[|\()(.*?)(\]|\))|CD\s*\d+|Disc\s*\d+', '', album, flags=re.IGNORECASE).strip()
            query = '{} {} {} album site:wikipedia.org'.format(
                artist, year, clean_album)
            wikilink = list(googlesearch.search(
                query, tld='com', num=1, stop=1, pause=2))
            if len(wikilink):
                return wikilink[0]
            else:
                return None

        def extract_genre_from_wikipage(wikilink):
            """
            Parse Wikipedia page HTML for album genre.
            
            Arguments:
                wikilink {str} -- link to Wikipedia page to scrape and
            
            Returns:
                {str} -- genre(s) parsed from Wikipedia page
            """


            # Scrape page for CSS selector
            genre = get_element_by_selector(wikilink, '.category a')
            if not len(genre) or not isinstance(genre, str):
                return None

            # Parse multiple genres if present
            genre = [genre] if isinstance(genre, str) else genre
            genre = [x for x in genre if not re.search(r'\[\d+\]', x)]
            if not len(genre):
                return None

            # Capitalize text for each genre returned
            genre = titlecase(', '.join(x for x in genre))
            return genre

        def extract_image_from_wikipage(wikilink, image_outfile, overwrite=True):
            """
            Parse Wikipedia page HTML for album image.
            
            Arguments:
                wikilink {str} -- link to Wikipedia page to scrape
                outfile {str} -- path to image outfile to save image to, if image is found
            
            Keyword Arguments:
                overwrite {bool} -- if True, overwrite `outfile` if it exists (default: {True})
            
            Returns:
                nothing
            """

            # Get image xpath
            img_xpath = get_element_by_xpath(
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
            outfile = splitext(image_outfile)[0] + splitext(img_url)[len(splitext(img_url))-1]
            if not isfile(outfile) or overwrite:
                downloadfile(img_url, outfile)

            return outfile

        def verify_downloaded_image(album_artwork_file):
                """
                Check if downloaded file is >1kb. Sometimes an image will be downloaded that is not
                a real image file.
                
                Arguments:
                    album_artwork_file {str} -- downloaded image file
                
                Returns:
                    {bool}
                """
                try:
                    if isfile(album_artwork_file):
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
                    if isfile(downloaded_file):
                        # Check that image is valid
                        if not verify_downloaded_image(downloaded_file):
                            if isfile(downloaded_file):
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


def transcribe(audiofile, method='gcs', gcs_split_threshold=50, apply_correction=True, verbose=False):
    """
    Transcribe audio file in .wav format using method of choice.

    Arguments:
        audiofile {str} -- audio file to transcribe

    Keyword Arguments:
        method {str} -- method to use for audiofile transcription, one of ['gcs']
        gcs_split_threshold {int} -- maximum audio clip size in seconds, if clip exceeds this length it will be split using class method `split()` (default: {55})
        apply_correction {bool} -- if True, call apply_transcription_corrections() after transcript created (default: {True})
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

            # Ensure file is in mono .wav format. If not, create a temporary .wav file
            ext = splitext(env.focus)[1]
            if verbose:
                if ext != '.wav':
                    echo('Converting %s audio to mono wav' % ext, timestamp=True, fn_name=fn_name)
                else:
                    echo('Converting .wav audio to mono', timestamp=True, fn_name=fn_name)
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
                iterable = tqdm(fnames, total=len(fnames), unit='audiofile')
            else:
                iterable = fnames
            try:
                for fname in iterable:
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
    if verbose:
        program_complete('Transcription complete')

    return transcript


def apply_transcription_corrections(transcript):
    """
    Apply any and all corrections to output of transcribe().

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
        out = FFmpeg().join(audiofiles, targetfile)
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
    FFmpeg().split(audiofile, segment_time=55)

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


from pydoni.sh import syscmd, FFmpeg
from pydoni.vb import echo, program_complete
from pydoni.os import listfiles
from pydoni.classes import ProgramEnv
from pydoni.pyobj import cap_nth_char, replace_nth_char, insert_nth_char
