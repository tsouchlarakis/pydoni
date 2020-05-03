import pydoni
import pydoni.sh


class Convention(object):
    """
    Hold naming convention regex strings.
    """

    def __init__(self):
        self.photo = ''
        self.video = ''
        conv_base = '' +\
            r'(?P<year>\d{4})' +\
            r'(?P<month>\d{2})' +\
            r'(?P<day>\d{2})' +\
            '' +\
            r'(?P<hours>\d{2})' +\
            r'(?P<minutes>\d{2})' +\
            r'(?P<seconds>\d{2})' +\
            '' +\
            r'(?P<initials>[A-Za-z]{2,3})'
        self.photo = conv_base +\
            '_' +\
            r'(?P<camera>.*?)' +\
            '_' +\
            r'(?P<seqnum>(\d{4,}|\d+-\d|-\d|))' +\
            r'(?P<affix>(-HDR-*\d*|-Pano-*\d*|-Edit-*\d*|-Stack-*\d*|)*)' +\
            r'(?P<ext>\.[a-z0-9]{3})'
        self.video = conv_base +\
            '_' +\
            r'(?P<camera>.*?)' +\
            '_' +\
            r'(?P<seqnum>.*(\d+))' +\
            '_' +\
            r'(?P<quality>Q\d+(K|P))' +\
            r'(?P<fps>\d{2,3}FPS)' +\
            r'(?P<ext>\.[a-z0-9]{3})'


class Extension(object):
    """
    Hold valid file extension lists of strings.
    """

    def __init__(self):
        self.photo = ['.jpg', '.jpeg', '.dng', '.arw', '.cr2']
        self.video = ['.mov', '.mp4', '.mts', '.m4v', '.avi']
        self.rm = ['.thm']


class MediaFile(Convention, Extension):
    """
    Gather information for a photo or video file.

    :param fpath: absolute path to file to initialize MediaFile class on
    :type fpath: str
    """

    def __init__(self, fpath):

        import os
        import pydoni.sh

        self.logger = pydoni.logger_setup(
            name=pydoni.what_is_my_name(classname=self.__class__.__name__, with_modname=True),
            level=pydoni.modloglev)

        # Inherit naming conventions and extensions
        Convention.__init__(self)
        Extension.__init__(self)

        # Assign filename and directory name attributes to `self`
        self.fpath_abs = os.path.abspath(fpath)
        self.fname = os.path.basename(self.fpath_abs)
        self.dname = os.path.dirname(self.fpath_abs)
        assert self.fname != self.fpath_abs
        assert self.dname > ''

        # Define extensions
        self.ext = os.path.splitext(self.fname)[1].lower()
        self.valid_ext = Extension()

        # Parse media type from extension
        self.mtype = self.parse_media_type()
        self.remove_flag = True if self.mtype == 'remove' else False

        self.exif = pydoni.sh.EXIF(self.fpath_abs).extract()

        self.logger.logvars(locals())

    def parse_media_type(self):
        """
        Given a file extension, get the type of media
        One of 'photo', 'video' or 'remove'

        :return: type of media
        :rtype: str
        """

        if self.ext in self.valid_ext.photo:
            return 'photo'
        elif self.ext in self.valid_ext.video:
            return 'video'
        elif self.ext in self.valid_ext.rm:
            return 'remove'
        else:
            e = "Invalid extension: '%s'" % self.ext
            self.logger.error(e)
            raise Exception(e)

    def build_fname(self, initials, tz_adjust=0):
        """
        Build new filename from EXIF metadata.

        :param initials: two character initials string
        :type initials: str
        :param tz_adjust: alter 'hours' by set number to account for timezone adjust (default: {0})
        :type tz_adjust: int
        :return: new file basename according to convention
        :rtype: str
        """

        from os.path import join

        assert isinstance(initials, str)
        assert len(initials) in [2, 3]
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

            :param attrs: attribute name(s) to search exif dictionary for
            :type: str or list
            :param def_str: return this string if attributes not found
            :type: str
            """
            assert isinstance(exif, dict)
            assert isinstance(attrs, str) or isinstance(attrs, list)
            assert isinstance(def_str, str)

            attrs = [attrs] if isinstance(attrs, str) else attrs
            bogus = ['0000:00:00 00:00:00']

            # `exif` is in format {FILENAME: {'exif_attr1': 'exif_val1', ...}}
            # Subset `exif` at FILENAME
            exif_items = exif[list(exif.keys())[0]]

            for attr in attrs:
                if attr in exif_items.keys():
                    val = exif_items[attr]
                    if val not in bogus:
                        return val

            return def_str

        def extract_video_quality(exif, def_str):
            """
            Given EXIF dictionary, extract video quality.

            :param exif: EXIF dictionary
            :type: dict
            :param def_str: return this string if value is not not found
            :type: str
            :return :video quality string
            :rtype: str
            """
            assert isinstance(exif, dict)
            assert isinstance(def_str, str)

            image_width = search_exif(
                exif    = exif,
                attrs   = ['ImageWidth', 'VideoSize'],
                def_str = def_str)

            if image_width == def_str:
                return def_str
            elif image_width == 3840:
                return '4K'
            elif image_width == 2704:
                return '1520P'
            elif image_width == 1920:
                return '1080P'
            elif image_width == 1280:
                return '720P'
            else:
                return image_width

        def extract_video_framerate(exif, def_str):
            """
            Given EXIF dictionary, extract video frame rate.

            :param exif: EXIF dictionary
            :type: dict
            :param def_str: return this string if value is not not found
            :type: str
            :return: video framerate string
            :rtype: str
            """
            assert isinstance(exif, dict)
            assert isinstance(def_str, str)

            framerate = search_exif(
                exif    = exif,
                attrs=['VideoAvgFrameRate', 'VideoFrameRate'],
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

            :param exif: EXIF dictionary
            :type: dict
            :param def_str: return this string if value is not not found
            :type: str
            :param mtype: `MediaFile.mtype` (media type string)
            :type: str
            :param tz_adjust: alter 'hours' by set number to account for timezone adjust
            :type: int
            :return: (capture date string, capture time string)
            :rtype: tuple
            """
            import re
            assert isinstance(exif, dict)
            assert isinstance(def_str, str)
            assert mtype in ['photo', 'video']

            if mtype == 'photo':
                attrs = ['CreateDate', 'FileModifyDate']
            elif mtype == 'video':
                attrs = ['FileModifyDate', 'CreateDate']

            # Get capture date
            raw_dt = str(search_exif(exif=exif, attrs=attrs, def_str=def_str))
            capture_date = re.sub(r'(.*?)(\s+)(.*)', r'\1', raw_dt)
            capture_date = capture_date.replace(':', '').replace('-', '')

            # Get capture time
            capture_time = raw_dt.replace(':', '')
            capture_time = re.sub(r'(.*?)(\s+)(.*)', r'\3', capture_time)[0:6]

            # Adjust hours by timezone if specified. May also need to alter day if timezone
            # adjust makes the day spill over into the next/previous day
            if tz_adjust is not None and tz_adjust != 0:
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

            :param fname: filename to extract sequence number from
            :type: str
            :param def_str: return this string if value is not not found
            :type: str
            :return: sequence number
            :rtype: str
            """
            import re
            import os

            assert isinstance(fname, str)
            assert isinstance(def_str, str)

            # Extract sequence number. Search first for 5 digits at the end of the filename.
            # If not found, search for 4 digits.

            # Clean up searchable area of filename by removing YYYYMMDDASHHMMSS and the string
            # for video files QXXXXFPS
            fname_ = os.path.basename(fname)
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

            :param exif: EXIF dictionary
            :type: dict
            :param def_str: return this string if value is not not found
            :type: str
            :param dname: directory name of photo, only used in parsing camera model if all else fails
            :type: str
            :return: camera model string
            :rtype: str
            """
            import os
            assert isinstance(exif, dict)
            assert isinstance(def_str, str)
            assert isinstance(dname, str)
            assert os.path.isdir(dname)

            # Get camera model from raw exif
            cm_raw = search_exif(
                exif    = exif,
                attrs   = ['CameraModelName', 'DeviceModelName', 'Model'],
                def_str = def_str
            )

            # If no camera model found, apply manual corrections
            if cm_raw == def_str:

                # Get make
                make_raw = search_exif(
                    exif    = exif,
                    attrs   = ['Make', 'DeviceManufacturer', 'CompressorName'],
                    def_str = '{}'
                )
                valid_makes = ['Sony', 'Canon', 'DJI', 'Gopro', 'Gopro AVC Encoder', '{}']
                assert any([make_raw.lower() in [x.lower() for x in valid_makes]])
                for vm in valid_makes:
                    if vm.lower() in make_raw.lower():
                        make = vm

                # Manual corrections
                if make.lower() == 'dji' or os.path.basename(dname).lower() == 'drone':
                    return 'L1D-20c'  # DJI Mavic 2 Pro
                elif make.lower() == 'gopro' or os.path.basename(dname).lower() == 'gopro':
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
            newfname = "{}_{}_{}_{}_{}{}".format(
                self.cd, self.ct, self.initials, self.cm, self.sn, self.ext.lower())

        elif self.mtype == 'video':
            self.vq = extract_video_quality(exif, def_str)
            self.vfr = extract_video_framerate(exif, def_str)
            newfname = "{}_{}_{}_{}_{}_Q{}{}FPS{}".format(
                self.cd, self.ct, self.initials, self.cm, self.sn, self.vq, self.vfr, self.ext.lower())

        return newfname

    def convert_dng(self, remove_original=False):
        """
        Convert a photo file to dng.

        :param remove_original: if True, remove original raw file (default: {True})
        :type: bool
        """
        assert self.ext in self.valid_ext.photo
        pydoni.sh.adobe_dng_converter(self.fpath_abs)

        if remove_original:
            from send2trash import send2trash
            send2trash(self.fpath_abs)
