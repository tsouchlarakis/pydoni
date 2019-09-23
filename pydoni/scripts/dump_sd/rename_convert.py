import argparse
import re
from os import chdir, rename
from os.path import isdir, splitext, basename
from send2trash import send2trash
from tqdm import tqdm
from pydoni.os import listfiles
from pydoni.vb import echo, verbose_header, program_complete


class RenameConvert(object):
    """
    Rename/Convert program master class.

    Arguments:
        dname {str} -- directory name to run program on
        initials {str} -- two-character initial string
        tz_adjust {int} -- subtract this many hours from photo created date to use in file renaming (default: {0})
        ignore_rename {bool} -- if True, ignore the Rename portion of program (default: {False})
        ignore_convert {bool} -- if True, ignore the Convert portion of program (default: {False})
        recursive {bool} -- if True, operate on all subdirectories found in `dname` (default: {False})
        verbose {bool} -- if True, print messages to STDOUT (default: {False})
    """

    def __init__(self, dname, initials, tz_adjust, ignore_rename, ignore_convert, recursive, verbose):
        self.dname = dname
        self.initials = initials
        self.tz_adjust = tz_adjust
        self.ignore_rename = ignore_rename
        self.ignore_convert = ignore_convert
        self.recursive = recursive
        self.verbose = verbose

    def run(self):
        """
        Execute class.
        """

        assert isdir(self.dname)
        assert isinstance(self.initials, str)
        assert len(self.initials) == 2
        assert isinstance(self.tz_adjust, int)
        assert isinstance(self.ignore_rename, bool)
        assert isinstance(self.ignore_convert, bool)
        assert isinstance(self.recursive, bool)
        assert isinstance(self.verbose, bool)
        
        chdir(self.dname)
        c = Convention()

        # Rename
        if not self.ignore_rename:
            media_files = listfiles(full_names=True, recursive=self.recursive)
            media_files = [x for x in media_files \
                if not re.match(c.photo, basename(x)) \
                and not re.match(c.video, basename(x))]
            if len(media_files):
                if self.verbose:
                    verbose_header('Renaming {} media files'.format(str(len(media_files))))
                    with tqdm(total=len(media_files), unit='mediafile') as pbar:
                        for f in media_files:
                            pbar.set_postfix(mediafile=f[-10:])
                            mf = MediaFile(f, run_exiftool=True)
                            if mf.remove_flag is True:
                                send2trash(f)
                                pbar.update(1)
                                continue
                            newfname = mf.build_fname(initials=self.initials, tz_adjust=self.tz_adjust)
                            if basename(f) != basename(newfname):
                                rename(f, newfname)
                            pbar.update(1)
                else:
                    for f in media_files:
                        mf = MediaFile(f, run_exiftool=True)
                        if mf.remove_flag is True:
                            send2trash(f)
                            continue
                        newfname = mf.build_fname(initials=self.initials, tz_adjust=self.tz_adjust)
                        if basename(f) != basename(newfname):
                            rename(f, newfname)

            else:
                if self.verbose:
                    echo('No files to rename!', fg='green')

        # Convert to DNG
        if not self.ignore_convert:
            media_files = listfiles(full_names=True, ext=['arw', 'cr2'], recursive=self.recursive)
            if len(media_files):
                if self.verbose:
                    verbose_header('Converting {} raw files'.format(str(len(media_files))))
                    with tqdm(total=len(media_files), unit='rawfile') as pbar:
                        for f in media_files:
                            pbar.set_postfix(mediafile=f[-10:])
                            mf = MediaFile(f, run_exiftool=False).convert_dng(remove_original=True)
                            pbar.update(1)
                else:
                    for f in media_files:
                        mf = MediaFile(f, run_exiftool=False).convert_dng(remove_original=True)
            else:
                if self.verbose:
                    echo('No files to convert!', fg='green')

        if self.verbose:
            program_complete(
                msg          = 'Rename and convert successful!',
                emoji_string = ':poop:',
                notify       = True,
                notification = dict(
                    title='Rename/Convert',
                    open_iterm=True
                )
            )


from pydoni.scripts.dump_sd.dump_sd import Convention, Extension


class MediaFile(Convention, Extension):
    """
    Gather information for a photo or video file.
    
    Arguments:
        fpath {str} -- absolute path to file to initialize MediaFile class on

    Keyword Arguments:
        run_exiftool {bool} -- if True, run ExifTool automatically and save output dictionary as `self.exif` attribute (default: {False})
    """

    def __init__(self, fpath, run_exiftool=False):
        from os.path import isfile, dirname, basename, splitext, abspath
        from pydoni.classes import Attribute
        
        assert isinstance(fpath, str)
        assert isfile(fpath)
        assert isinstance(run_exiftool, bool)

        # Inherit naming conventions and extensions
        Convention.__init__(self)
        Extension.__init__(self)

        # Assign filename and directory name attributes to `self`
        self.fpath_abs = abspath(fpath)
        self.fname = basename(self.fpath_abs)
        self.dname = dirname(self.fpath_abs)
        assert self.fname != self.fpath_abs
        assert self.dname > ''
        
        # Define extensions
        self.ext = splitext(self.fname)[1].lower()
        self.valid_ext = Extension()
        assert self.ext in self.valid_ext.photo + self.valid_ext.video

        # Parse media type from extension
        self.mtype = self.parse_media_type()
        self.remove_flag = True if self.mtype == 'remove' else False

        # Run ExifTool if specified
        if run_exiftool is True:
            from pydoni.sh import EXIF
            self.exif = EXIF(self.fpath_abs).run(wrapper='doni')

    def parse_media_type(self):
        """
        Given a file extension, get the type of media (one of 'photo' or 'video')
        
        Returns:
            {str} -- type of media
        """

        if self.ext in self.valid_ext.photo:
            return 'photo'
        elif self.ext in self.valid_ext.video:
            return 'video'
        elif self.ext in self.valid_ext.rm:
            return 'remove'
        else:
            from pydoni.vb import echo
            echo('Invalid file extension slipped through the cracks!', fn_name='MediaFile.parse_media_type', abort=True)
        
    def build_fname(self, initials, tz_adjust=0):
        """
        Build new filename from EXIF metadata.

        Arguments:
            initials {str} -- two character initials string

        Keyword Arguments:
            tz_adjust {int} -- alter 'hours' by set number to account for timezone adjust (default: {0})

        Returns:
            {str} -- new filename according to convention (basename)
        """
        
        from os.path import join

        assert isinstance(initials, str)
        assert len(initials) == 2
        req_attrs = ['exif', 'mtype', 'dname', 'fname']
        for ra in req_attrs:
            assert hasattr(self, ra)
        assert self.mtype in ['photo', 'video']
        assert isinstance(tz_adjust, int)
        assert tz_adjust in range(-24, 24)

        def search_exif(exif, attrs, def_str):
            """
            Search exif dictionary for name attributes in the order specified. For example
            if `attrs` argument is ['image_width', 'video_size'], first search `exif` for
            the attribute 'image_width'. If it exists and is a valid value, return this
            value. If not, search for 'video_size' and return that value if it exists and
            is valid. If neither value exists, return an arbitrary string.

            Arguments:
                attrs {str} or {list} -- attribute name(s) to search exif dictionary for
                def_str {str} -- return this string if attributes not found
            """
            assert isinstance(exif, dict)
            assert isinstance(attrs, str) or isinstance(attrs, list)
            assert isinstance(def_str, str)

            attrs = [attrs] if isinstance(attrs, str) else attrs
            bogus = ['0000:00:00 00:00:00']

            for attr in attrs:
                if attr in exif.keys():
                    val = exif[attr]
                    if val not in bogus:
                        return val

            return def_str

        def extract_video_quality(exif, def_str):
            """
            Given EXIF dictionary, extract video quality.
            
            Arguments:
                exif {dict} -- EXIF dictionary
                def_str {str} -- return this string if value is not not found
            
            Returns:
                {str} -- video quality string
            """
            assert isinstance(exif, dict)
            assert isinstance(def_str, str)
            
            image_width = search_exif(
                exif    = exif,
                attrs   = ['image_width', 'video_size'],
                def_str = def_str)
            if image_width == def_str:
                return def_str
            elif image_width == '3840':
                return '4K'
            elif image_width == '2704':
                return '1520P'
            elif image_width == '1920':
                return '1080P'
            elif image_width == '1280':
                return '720P'
            else:
                return image_width

        def extract_video_framerate(exif, def_str):
            """
            Given EXIF dictionary, extract video frame rate.
            
            Arguments:
                exif {dict} -- EXIF dictionary
                def_str {str} -- return this string if value is not not found
            
            Returns:
                {str} -- video framerate string
            """
            assert isinstance(exif, dict)
            assert isinstance(def_str, str)
            
            framerate = search_exif(
                exif    = exif,
                attrs=['video_avg_frame_rate', 'video_frame_rate'],
                def_str = def_str)
            if framerate == def_str:
                return def_str
            else:
                try:
                    return round(float(framerate))
                except:
                    return framerate

        def extract_capture_date_and_time(exif, def_str, mtype, tz_adjust=None):
            """
            Given EXIF dictionary, extract file capture date and time.
            
            Arguments:
                exif {dict} -- EXIF dictionary
                def_str {str} -- return this string if value is not not found
                mtype {str} -- `MediaFile.mtype` (media type string)
                
            Keyword Arguments:
                tz_adjust {int} -- alter 'hours' by set number to account for timezone adjust
            
            Returns:
                {tuple} -- (capture date string, capture time string)
            """
            import re
            assert isinstance(exif, dict)
            assert isinstance(def_str, str)
            assert mtype in ['photo', 'video']
            
            if mtype == 'photo':
                attrs = ['create_date', 'file_modification_date/time']
            elif mtype == 'video':
                attrs = ['file_modification_date/time', 'create_date']
            
            # Get capture date
            raw_dt = search_exif(
                exif    = exif,
                attrs   = attrs,
                def_str = def_str
            )
            capture_date = re.sub(r'(.*?)(\s+)(.*)', r'\1', raw_dt)
            capture_date = capture_date.replace(':', '')
            
            # Get capture time
            capture_time = raw_dt.replace(':', '')
            capture_time = re.sub(r'(.*?)(\s+)(.*)', r'\3', capture_time)[0:6]
            
            # Adjust hours by timezone if specified. May also need to alter day if timezone
            # adjust makes the day spill over into the next/previous day
            if tz_adjust is not None:
                import datetime
                dt = datetime.datetime.strptime(capture_date + capture_time, '%Y%m%d%H%M%S')
                dt = dt + datetime.timedelta(hours=tz_adjust)
                capture_date = dt.strftime('%Y%m%d')
                capture_time = dt.strftime('%H%M%S')

            return (capture_date, capture_time)

        def extract_sequence_number(fname, def_str):
            """
            Given filename, extract file sequence number as the final occurrence of 4 or 5
            digits in a filename.
            
            Arguments:
                fname {str} -- filename to extract sequence number from
                def_str {str} -- return this string if value is not not found
            
            Returns:
                {str} -- sequence number
            """
            import re
            from os.path import basename
            assert isinstance(fname, str)
            assert isinstance(def_str, str)

            # Extract sequence number. Search first for 5 digits at the end of the filename.
            # If not found, search for 4 digits.
            
            # Clean up searchable area of filename by removing YYYYMMDDASHHMMSS and the string
            # for video files QXXXXFPS
            fname_ = basename(fname)
            fname_ = re.sub('_Q.*?FPS', '', fname_)
            fname_ = re.sub(r'^\d{8}\w{2}\d{6}_', '', fname_)
            
            # Search for 5 or 4 digits
            ptn = r'^(.*)(\d{5})(.*)$'
            if re.search(ptn, fname_):
                return re.sub(ptn, r'\2', fname_)
            else:
                ptn = r'^(.*)(\d{4})(.*)$'
                if re.search(ptn, fname_):
                    return re.sub(ptn, r'\2', fname_)
                else:
                    return def_str

        def extract_camera_model(exif, def_str, dname):
            """
            Given EXIF dictionary, extract camera model.
            
            Arguments:
                exif {dict} -- EXIF dictionary
                def_str {str} -- return this string if value is not not found
                dname {str} -- directory name of photo, only used in parsing camera model if all else fails
            
            Returns:
                {str} -- camera model string
            """
            from os.path import basename, isdir
            assert isinstance(exif, dict)
            assert isinstance(def_str, str)
            assert isinstance(dname, str)
            assert isdir(dname)

            # Get camera model from raw exif
            cm_raw = search_exif(
                exif    = exif,
                attrs   = ['camera_model_name', 'device_model_name', 'model'],
                def_str = def_str
            )

            # If no camera model found, apply manual corrections
            if cm_raw == def_str:
                
                # Get make
                make_raw = search_exif(
                    exif    = exif,
                    attrs   = ['make', 'device_manufacturer', 'compressor_name'],
                    def_str = '{}'
                )
                valid_makes = ['Sony', 'Canon', 'DJI', 'Gopro', 'Gopro AVC Encoder', '{}']
                assert any([make_raw.lower() in [x.lower() for x in valid_makes]])
                for vm in valid_makes:
                    if vm.lower() in make_raw.lower():
                        make = vm

                # Manual corrections
                if make.lower() == 'dji' or basename(dname).lower() == 'drone':
                    return 'FC2103'  # DJI Mavic Air
                elif make.lower() == 'gopro' or basename(dname).lower() == 'gopro':
                    return 'HERO5 Black'
                else:
                    return def_str
            
            else:
                return cm_raw

        exif = self.exif
        fname = self.fname
        self.initials = initials

        # Default string to be returned by any of the extract* functions if that
        # attribute is unable to be found
        def_str = '{}'
        
        # Extract attributes from EXIF used regardless of photo or video
        self.cd, self.ct = extract_capture_date_and_time(exif, def_str, self.mtype, tz_adjust)
        self.sn = extract_sequence_number(fname, def_str)
        self.cm = extract_camera_model(exif, def_str, self.dname)
        
        # Build new filename
        if self.mtype == 'photo':
            newfname = "{}{}{}_{}_{}{}".format(
                self.cd, self.initials, self.ct, self.cm, self.sn, self.ext.lower())

        elif self.mtype == 'video':
            self.vq = extract_video_quality(exif, def_str)
            self.vfr = extract_video_framerate(exif, def_str)
            newfname = "{}{}{}_{}_{}_Q{}{}FPS{}".format(
                self.cd, self.initials, self.ct, self.cm, self.sn, self.vq, self.vfr, self.ext.lower())
        
        return newfname

    def convert_dng(self, remove_original=False):
        """
        Convert a photo file to dng.

        Keyword Arguments:
            remove_original {bool} -- if True, remove original raw file (default: {True})
        """
        from pydoni.sh import adobe_dng_converter
        assert self.ext in self.valid_ext.photo
        adobe_dng_converter(self.fpath_abs)
        if remove_original:
            from send2trash import send2trash
            send2trash(self.fpath_abs)