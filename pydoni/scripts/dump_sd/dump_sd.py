import re
import click
import pandas as pd
from tqdm import tqdm
from os import chdir, remove, mkdir, rename
from os.path import join, isdir, getmtime, basename, splitext, isfile
from shutil import copy2
from send2trash import send2trash
from datetime import datetime, timedelta
from pydoni.os import listfiles
from pydoni.vb import echo, verbose_header, program_complete, macos_notify


def parse_date(date):
    """
    Get date in format YYYY-MM-DD if entered as 'today' or 'yesterday'.

    Arguments:
        date {str} -- date in format YYYYMMDD or 'today' or 'yesterday'

    Returns:
        {str}
    """
    if date == 'today':
        date = datetime.strftime(datetime.now(), '%Y-%m-%d')
    elif date == 'yesterday':
        date = datetime.strftime(datetime.now() - timedelta(days=1), '%Y-%m-%d')
    assert re.search(r'^\d{4}-\d{2}-\d{2}$', date)
    return date


def parse_target_subcollection(fname):
    """
    Given a filename, get the target subcollection as one of ['Photo', 'Video', 'Gopro', 'Drone'].

    Arguments:
        fname {str} -- name of file to parse

    Returns:
        {str}
    """
    c = Convention()
    e = Extension()
    media_type = 'Photo' if splitext(fname)[1].lower() in e.photo else 'Video'
    conv = c.photo if media_type == 'Photo' else c.video
    camera = re.match(conv, fname).group('camera')
    if re.search(r'gopro|hero', camera, flags=re.IGNORECASE):
        return 'Gopro'
    elif 'FC' in camera:
        return 'Drone'
    else:
        return media_type


class Extension(object):
    """
    Hold valid file extension lists of strings.
    """

    def __init__(self):
        self.photo = ['.jpg', '.dng', '.arw', '.cr2']
        self.video = ['.mov', '.mp4', '.mts', '.m4v', '.avi']


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
            r'(?P<initials>[A-Za-z]{2})' +\
            r'(?P<hours>\d{2})' +\
            r'(?P<minutes>\d{2})' +\
            r'(?P<seconds>\d{2})'
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


class DumpSD(object):
    """
    Dump photo and video files from a source volume to a target directory. Rename and Convert
    RAW files to DNG as necessary.

    Arguments:
        vol_source {str} -- source volume name
        coll_target {str} -- absolute directory path of destination collection
        date {str} -- dump photos with this creation date, format YYYY-MM-DD
        rename {bool} -- rename media files according to defined convention
        convert {bool} -- convert RAW photos to DNG
        verbose {bool} -- print messages to STDOUT
        notify {bool} -- send macOS notification upon program completion
        test_mode {bool} -- run program in test mode
        rc_initials {str} -- initials parameter for RenameConvert. Only must be specified if 'rename' or 'convert' is True (default: {AS})
        rc_tz_adjust {int} -- tz_adjust parameter for RenameConvert. Only must be specified if 'rename' or 'convert' is True (default: {0})
    """

    def __init__(
        self,
        vol_source,
        coll_target,
        date,
        rename,
        convert,
        verbose,
        notify,
        test_mode,
        rc_initials,
        rc_tz_adjust
        ):
        self.vol_source = vol_source
        self.coll_target = coll_target
        self.date = date
        self.rename = rename
        self.convert = convert
        self.verbose = verbose
        self.notify = notify
        self.test_mode = test_mode
        self.rc_initials = rc_initials
        self.rc_tz_adjust = rc_tz_adjust

    def run(self):
        """
        Execute class.
        """

        self.date = parse_date(self.date)
        self.vol_source = join('/', 'Volumes', self.vol_source)
        assert isdir(self.vol_source)
        assert isdir(self.coll_target)
        self.vol_target = '/'.join(self.coll_target.split('/')[0:3])
        assert isdir(self.vol_target)
        
        if self.test_mode:
            echo("Initializing Program: 'Dump SD' in Test Mode...", sleep=1)
            check_params(var)
            echo('')
            echo('Begin Operational Code')
            echo('')

        if self.test_mode:
            echo('Checking source and target directories...', sleep=.25, fg='blue')
            echo('Source volume name     : {} {}'.format(
                self.vol_source, emojize(':white_check_mark:', use_aliases=True)), sleep=.25)
            echo('Source volume type     : {} {}'.format(
                self.vol_source_type, emojize(':white_check_mark:', use_aliases=True)), sleep=.25)
            echo('Target collection      : {} {}'.format(
                self.coll_target, emojize(':white_check_mark:', use_aliases=True)), sleep=.25)
            echo('')

        # List all files in source volume that match given date
        chdir(self.vol_source)
        ext = Extension()
        fnames = [f for f in listfiles(recursive=True, ext=ext.photo+ext.video) \
            if datetime.fromtimestamp(getmtime(f)).strftime('%Y-%m-%d') == self.date \
            and not re.search(r'T\d{2,3}\.', f)  # Eliminate Sony movie thumbnail files
        ]
        if not len(fnames):
            echo("No photo or video files found at '{}' for day '{}'!".format(
                self.vol_source, self.date), abort=True)

        # Copy files to temporary directory
        tmpdir = join(self.vol_target, '.tmp.dumpsd')
        if isdir(tmpdir):
            send2trash(tmpdir)
        mkdir(tmpdir)
        if self.verbose:
            verbose_header('Dumping %s media files' % str(len(fnames)))
            with tqdm(total=len(fnames), unit='mediafile') as pbar:
                for f in fnames:
                    pbar.set_postfix(mediafile=f[-10:])
                    copy2(f, join(tmpdir, basename(f)))
                    pbar.update(1)
        else:
            for f in fnames:
                copy2(f, join(tmpdir, basename(f)))

        # Run RenameConvert on directory
        if self.rename or self.convert:
            ignore_rename = not self.rename
            ignore_convert = not self.convert
            RenameConvert(
                dname=tmpdir,
                initials=self.rc_initials,
                tz_adjust=self.rc_tz_adjust,
                ignore_rename=ignore_rename,
                ignore_convert=ignore_convert,
                recursive=False,
                verbose=self.verbose
            ).run()

        # Copy files to target collection
        chdir(tmpdir)
        media_files = [x for x in listfiles() if splitext(x)[1].lower() != '.arw']
        dumped_subcolls = []
        for f in media_files:
            subcoll = parse_target_subcollection(f)
            rename(f, join(self.coll_target, subcoll, f))
            dumped_subcolls.append(subcoll)

        if isdir(tmpdir):
            send2trash(tmpdir)

        if self.verbose:
            echo('Dump Summary', underline=True, fg='white', bold=True)
            dumped_subcolls = pd.Series(dumped_subcolls).value_counts()
            echo('Collection: %s' % self.coll_target, indent=2)
            for subcol, count in dumped_subcolls.iteritems():
                echo("Subcollection '{}': {} media files dumped".format(
                    click.style(subcol, fg='cyan'),
                    str(count)),
                    indent=2
                )

        if self.notify:
            content_image = '/Users/Andoni/GDrive/Code/git-doni/pydoni/pydoni/scripts/dump_sd/img/Dump-SD-Icon.png'
            content_image = content_image if isfile(content_image) else None
            macos_notify(title='Dump SD', message='Dump completed successfully!',
                content_image=content_image)


            # program_complete(
            #     msg          = "{} media files dumped to '{}'".format(str(len(media_files)), self.coll_target),
            #     emoji_string = ':poop:',
            #     notify       = True,
            #     notification = dict(
            #         title='Dump SD',
            #         open_iterm=True
            #     )
            # )


from pydoni.scripts.dump_sd.rename_convert import RenameConvert


# # Get target collection and list all files in that collection and in the current year
# dest = DestVolume(vol_target)
# dest.collection = ns.coll_target
# # dest.get_collection(dname='Photos/_All_Photos', ns.vol_source_type=ns.vol_source_type)
# dest.list_dest_files(ext_photo=var.ext.photo, ext_video=var.ext.video)

# if ns.test_mode:
#     echo('Checking target files...', fg='blue')
#     echo('Num. Photo Files   : {} {}'.format(
#         str(len(dest.files.photo)), emojize(':white_check_mark:', use_aliases=True)), sleep=.25)
#     echo('Num. Video Files   : {} {}'.format(
#         str(len(dest.files.video)), emojize(':white_check_mark:', use_aliases=True)), sleep=.25)
#     echo('Num. Files in Year : {} {}'.format(
#         str(len(dest.files.all_in_year)), emojize(':white_check_mark:', use_aliases=True)), sleep=.25)
#     echo('')

# # Set the volume format and list all files in source volume
# source = SourceVolume(ns.vol_source)
# source.set_volume_format(ns.vol_source_type)
# source.list_source_files(ext_photo=var.ext.photo, ext_video=var.ext.video)
# if not len(source.files.photo + source.files.video):
#     echo('No source files found!', abort=True)

# if ns.test_mode:
#     echo('Checking source files...', fg='blue')
#     echo('Num. Photo Files : {} {}'.format(
#         str(len(source.files.photo)), emojize(':white_check_mark:', use_aliases=True) \
#             if len(source.files.photo) > 0 \
#             else emojize(':exclamation:', use_aliases=True) ), sleep=.25)
#     echo('Num. Video Files : {} {}'.format(
#         str(len(source.files.video)), emojize(':white_check_mark:', use_aliases=True) \
#             if len(source.files.video) > 0 \
#             else emojize(':exclamation:', use_aliases=True) ), sleep=.25)
#     echo('')

# # Determine photo and video subcollection directories to dump to
# dest.define_subcollections(source.volume_type)
# if ns.test_mode:
#     echo('Checking subcollections...', fg='blue')
#     echo('Photo subcollection to dump to: {} {}'.format(
#         dest.subcollection[0],
#         emojize(':white_check_mark:', use_aliases=True) \
#             if isdir(join(dest.collection, dest.subcollection[0])) \
#             else emojize(':x:', use_aliases=True)), sleep=.25)
#     echo('Video subcollection to dump to: {} {}'.format(
#         dest.subcollection[1],
#         emojize(':white_check_mark:', use_aliases=True) \
#             if isdir(join(dest.collection, dest.subcollection[1])) \
#             else emojize(':x:', use_aliases=True)), sleep=.25)
#     echo('')

# # Build new filename for every source file and return in dataframe with columns:
# #   'sourcename', 'destname', 'media_type', 'camera_model', 'capture_date', 'exists'
# verbose_header('Build new source filenames and check which files are already dumped',
#     time_in_sec=0.24703087885985747*len(source.files.__flatten__()))
# master = get_master_df(
#     source_files=source.files.__flatten__(),
#     ext_photo=var.ext.photo,
#     ext_video=var.ext.video,
#     ns.vol_source_type=ns.vol_source_type,
#     initials='AS',
#     files_all_in_year=dest.files.all_in_year)
# if not len(master):
#     echo('Unable to get master dataframe!', abort=True)
# echo('')

# # Analyze 'master' dataframe, and extract unique dates. For each date, get the number of
# # files with that date already in dest.files.all_in_year. Print all dates to screen using
# # user_select_from_list(), and if there is a file with that date and camera model in
# # dest.files.all_in_year, then indicate that that date has already been dumped. If there are
# # no files with that date/camera model combination in dest.files.all_in_year, then indicate
# # that that date has not yet been dumped.
# # Returns a list of dates (may be of length 1).
# if date is None:
#     date = get_dates_to_transfer(master)
#     if not len(date):
#         echo('Must select a date or multiple dates to transfer!', abort=True)
# elif date == 'today':
#     date = [sysdate()]
# elif date == 'yesterday':
#     date = [(datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")]
# else:
#     date = date.replace(' ', '').split(',')
#     for dt in date:
#         if not re.match(r'^\d{4}-\d{2}-\d{2}$', dt):
#             echo("Invalid date '{}' passed in via CLI".format(dt), abort=False)
# echo('')
# # Select files to copy and their target names based on whether they are in 'date' and
# # whether they exist at target.
# transfer = master[(master['capture_date'].isin(date))] \
#     [['sourcename', 'destname', 'media_type', 'exists']] \
#     .reset_index(drop=True)
# date_exists_on_sd_card = any([x in master['capture_date'].unique() for x in date])
# if not date_exists_on_sd_card:
#     echo("No photos or videos for date(s) '{}' on SD card!".format(', '.join(date)), abort=True)

# # Get target filenames with absolute paths to target collection and subcollection
# destname = []
# for idx, row in transfer.iterrows():
#     subcollection = dest.subcollection[0] if row['media_type'] == 'photo' else dest.subcollection[1]
#     destname.append(join(dest.collection, subcollection, row['destname']))
# transfer['destname'] = destname

# # Check that there are indeed some files to transfer
# if len(transfer) == 0:
#     echo('All files in source are already in target year!', abort=True)

# # Create target subcollection folders if not exists
# for dname in [join(dest.collection, x) for x in dest.subcollection]:
#     if not isdir(dname):
#         mkdir(dname)

# # Get estimated time to copy all files based on aggregate filesize of source files
# transfer_fnames = Attribute()
# transfer_fnames.photo = transfer.loc[ \
#     (transfer['media_type'] == 'photo') & (transfer['exists'] == False)] \
#     ['sourcename'].squeeze()
# if isinstance(transfer_fnames.photo, str):
#     transfer_fnames.photo = [transfer_fnames.photo]
# else:
#     transfer_fnames.photo = transfer_fnames.photo.tolist()

# transfer_fnames.video = transfer.loc[ \
#     (transfer['media_type'] == 'video') & (transfer['exists'] == False)] \
#     ['sourcename'].squeeze()
# if isinstance(transfer_fnames.video, str):
#     transfer_fnames.video = [transfer_fnames.video]
# else:
#     transfer_fnames.video = transfer_fnames.video.tolist()

# fsize_bytes = sum([os_stat(x).st_size for x in transfer_fnames.__flatten__()])

# # Copy files to target directory. If program is run in test mode, do not copy files but
# # output a file to desktop detailing what files would have been copied.
# verbose_header('Copying {} photo and {} video files to target directory ({})'.format(
#     str(len(transfer_fnames.photo)),
#     str(len(transfer_fnames.video)),
#     human_filesize(fsize_bytes)),
#     time_in_sec=fsize_bytes/64767174)  # Speed of 64767174 bytes/sec
# if ns.test_mode:
#     with open(join(var.dir.home, 'Desktop', systime(stripchars=True) + '_Dump-SD-Copy-Files-Dry-Run.txt'), 'w') as f:
#         for idx, row in tqdm(transfer.iterrows(), total=transfer.shape[0]):
#             if row['exists']:
#                 f.write('NOT COPIED (Destfile already exists): {} -> {}\n'.format(
#                     row['sourcename'], row['destname']))
#             else:
#                 f.write('COPIED: {} -> {}\n'.format(row['sourcename'], row['destname']))
# else:
#     for idx, row in tqdm(transfer.iterrows(), total=transfer.shape[0]):
#         if not row['exists']:
#             copy2(row['sourcename'], row['destname'])
# echo('')

# # Convert all .arw files in target directory to .dng
# chdir(dest.collection)
# arw = listfiles(ext=['arw', 'cr2'], recursive=True)
# if len(arw):
#     # Convert raw files
#     verbose_header('Converting {} .arw files to .dng'.format(len(arw)), time_in_sec=2.5*len(arw))
#     if ns.test_mode:
#         with open(join(var.dir.home, 'Desktop', systime(stripchars=True) + '_Dump-SD-Convert-Raw-Dry-Run.txt'), 'w') as f:
#             for fname in arw:
#                 if isfile(splitext(fname)[0] + '.dng'):
#                     f.write('NOT CONVERTED (Destfile already exists): {}\n'.format(join(dest.collection, fname)))
#                 else:
#                     f.write('CONVERTED: {}\n'.format(join(dest.collection, fname)))
#     else:
#         for fname in tqdm(arw):
#             if not isfile(splitext(fname)[0] + '.dng'):
#                 MediaFile(fname, ext_photo=var.ext.photo, ext_video=var.ext.video).convert_dng()
#     #
#     # Delete .arw files by moving to trash directory
#     if ns.test_mode:
#         with open(join(var.dir.home, 'Desktop', systime(stripchars=True) + '_Dump-SD-Delete-ARW-Dry-Run.txt'), 'w') as f:
#             for fname in arw:
#                 f.write('DELETED: {} -> {}\n'.format(fname, join(var.dir.trash, basename(fname))))
#     else:
#         if not isdir(var.dir.trash):
#             mkdir(var.dir.trash)
#         for fname in arw:
#             rename(fname, join(var.dir.trash, basename(fname)))
#     echo('')

# program_complete(
#     msg='Dump SD successful!',
#     emoji_string=':poop:',
#     notify=True,
#     notification=dict(
#         title='Dump SD'
#     )
# )

# class DestVolume(object):
#     """Hold information about an attached external hard drive"""
#     def __init__(self, volume_name):
#         from os.path import basename, join, isdir
#         self.name = volume_name
#         self.root = join('/', 'Volumes', self.name)
#         if not isdir(self.root):
#             import sys
#             from pydoni.vb import echo, clickfmt
#             echo("Specified volume root path does not exist '{}'".format(clickfmt(self.root, 'red')))
#             sys.exit(1)
#     def get_collection(self, dname, ns.vol_source_type):
#         """Get the source or target directory on a volume by prompting user"""
#         import os, sys
#         from pydoni.os import listdirs
#         from pydoni.pyobj import user_select_from_list
#         os.chdir(self.root)
#         os.chdir(dname) if os.path.isdir(dname) else sys.exit(2)
#         year = user_select_from_list(sorted(listdirs(), reverse=True),
#             indent=1, allow_range=False, msg='Please select a target year')
#         os.chdir(year)
#         collection = user_select_from_list(sorted(listdirs(), reverse=False),
#             indent=1, allow_range=False, msg='Please select a target collection')
#         os.chdir(collection)
#         self.collection = os.getcwd()
#     def list_dest_files(self, ext_photo, ext_video):
#         """List files in target directory"""
#         from os.path import dirname
#         from pydoni.os import listfiles
#         from pydoni.classes import Attribute
#         self.files = Attribute()
#         self.files.photo = listfiles(path=self.collection, ext=ext_photo, recursive=True)
#         self.files.video = listfiles(path=self.collection, ext=ext_video, recursive=True)
#         self.files.all_in_year = listfiles(path=dirname(self.collection), ext=ext_photo+ext_video, recursive=True)
#     def define_subcollections(self, ns.vol_source_type):
#         """Determine subcollection directories to dump photo/video files to. Return a tuple with
#         one element for the subcollection directory for photos, and one for videos.
#         Ex. If the volume type is 'Sony', then photos should be dumped to subdir 'Photo' and 
#             videos should be dumped to subdir 'Video'
#         Ex. If volume type is drone, then both photos and videos should be dumped to subdir
#             'Drone'"""
#         if ns.vol_source_type.lower() == 'sony':
#             self.subcollection = ('Photo', 'Video')
#         elif ns.vol_source_type.lower() == 'dji':
#             self.subcollection = ('Drone', 'Drone')

# class SourceVolume(object):
#     """Hold information about an attached external hard drive"""
#     def __init__(self, volume_name):
#         from os.path import basename, join, isdir
#         self.name = volume_name
#         self.root = join('/', 'Volumes', self.name)
#         if not isdir(self.root):
#             import sys
#             from pydoni.vb import echo, clickfmt
#             echo("Specified volume root path does not exist '{}'".format(clickfmt(self.root, 'red')))
#             sys.exit(1)
#     def set_volume_format(self, volume_type):
#         from os.path import join, isdir
#         from pydoni.vb import echo, clickfmt
#         from pydoni.classes import Attribute
#         self.volume_type = volume_type
#         self.dname = Attribute()
#         if volume_type.lower() == 'sony':
#             dname_photo = join(self.root, 'DCIM')
#             dname_video = join(self.root, 'PRIVATE', 'M4ROOT', 'CLIP')
#         elif volume_type.lower() == 'dji':
#             dname_photo = join(self.root, 'DCIM')
#             dname_video = dname_photo
#         else:
#             echo("Volume type '{}' currently unsupported".format(volume_type), abort=True)
#         if not isdir(dname_photo):
#             echo("Source photo directory {} does not exist".format(
#                 clickfmt(dname_photo, 'filepath')), abort=True)
#         if not isdir(dname_video):
#             echo("Source video directory {} does not exist".format(
#                 clickfmt(dname_video, 'filepath')), abort=True)
#         self.dname.photo = dname_photo
#         self.dname.video = dname_video
#     def list_source_files(self, ext_photo, ext_video):
#         """List source photo and video files"""
#         from pydoni.os import listfiles
#         from pydoni.classes import Attribute
#         from pydoni.vb import echo, clickfmt
#         self.files = Attribute()
#         self.files.photo = listfiles(path=self.dname.photo, ext=ext_photo, recursive=True, full_names=True)
#         self.files.video = listfiles(path=self.dname.video, ext=ext_video, recursive=True, full_names=True)
#         if not len(self.files.photo) and not len(self.files.video):
#             echo("No photo or video files found at {} or {}".format(
#                 clickfmt(self.dname.photo, 'filepath'),
#                 clickfmt(self.dname.video, 'filepath')), abort=True)
#     def list_dates(self):
#         """List dates represented in Source volume"""
#         import os, pandas as pd, datetime
#         from pydoni.sh import stat
#         from pydoni.os import listfiles
#         dates = pd.Series()
#         for dname in self.dname.__flatten__():
#             os.chdir(dname)
#             for fname in listfiles(recursive=True):
#                 if os.path.isfile(fname):
#                     dt = os.stat(fname).st_birthtime
#                     date = datetime.datetime.fromtimestamp(dt).strftime('%Y-%m-%d')
#                     dates = dates.append(pd.Series([date])) 
#         self.dates = dates.value_counts().sort_index(ascending=False)

# class MediaFile(object):
#     """
#     Hold information for a photo or video file.
    
#     Arguments:
#         fname {str} -- filename to operate on
#         ext_photo {list} -- list of valid photo extensions
#         ext_video {list} -- list of valid video extensions
#     """
#     def __init__(self, fname, ext_photo, ext_video):
#         import os
#         self.fname = fname
#         ext_photo = ext_photo
#         ext_video = ext_video
#         self.ext = os.path.splitext(self.fname)[1].replace('.', '').lower()
#         if self.ext in ext_photo:
#             self.media_type = 'photo'
#         elif self.ext in ext_video:
#             self.media_type = 'video'
#         else:
#             from pydoni.vb import echo, clickfmt
#             echo('Unknown media_type for file {}'.format(clickfmt(self.fname, 'filepath')), abort=True)
#     def run_exiftool(self):
#         """Run exiftool system command"""
#         from pydoni.sh import EXIF
#         self.exif = EXIF(self.fname).run(wrapper='doni')
#     def convert_dng(self):
#         """Convert an .arw file to .dng using Adobe DNG Converter"""
#         from pydoni.sh import adobe_dng_converter
#         from pydoni.vb import echo
#         if self.ext == 'arw':
#             adobe_dng_converter(self.fname)
#         elif self.ext == 'cr2':
#             adobe_dng_converter(self.fname)
#         else:
#             echo("Filetype must be 'arw' to run Adobe DNG Converter (not {})!)".format(
#                 self.ext), warn=True)
#     def build_fname(self, initials, ns.vol_source_type):
#         """Build target filename given a file and its EXIF metadata"""
#         import os
#         from pydoni.vb import echo
#         def extract_metadata(self, attr_list):
#             """Iterate over attr_list to extract exif attribute. Prioritize extracted value in the
#             order that attr_list is defined.
#             Ex: if attr_list is ['image_width', 'video_size'], first search self.exif for
#             'image_width', if that is undefined then look for 'video_size'"""
#             import re, click
#             from pydoni.vb import echo, clickfmt
#             from pydoni.os import FinderMacOS
#             val = []
#             exif = self.exif
#             attr_list = [attr_list] if isinstance(attr_list, str) else attr_list
#             for elem in attr_list:
#                 if elem in exif:
#                     val.append(exif[elem])
#             # Remove any bogus elements
#             bogus = ['0000:00:00 00:00:00']
#             for bogus_item in bogus:
#                 while bogus_item in val:
#                     val.remove(bogus_item)
#             if len(val):
#                 # If at least one of the attr_list elements exists, return the first
#                 return val[0]
#             else:
#                 # None of the specified EXIF attributes exist, return arbitrary string
#                 # FinderMacOS(fname).write_tag('Red')
#                 return '{}'
#         def extract_videoquality(self):
#             imagewidth = extract_metadata(self, attr_list=['image_width', 'video_size'])
#             if imagewidth == '3840':
#                 return '4K'
#             elif imagewidth == '2704':
#                 return '1520P'
#             elif imagewidth == '1920':
#                 return '1080P'
#             elif imagewidth == '1280':
#                 return '720P'
#             else:
#                 return imagewidth
#         def extract_videoframerate(self):
#             framerate = extract_metadata(self, attr_list=['video_avg_frame_rate', 'video_frame_rate'])
#             try:
#                 return round(float(framerate))
#             except:
#                 return framerate
#         def extract_capturedate(self):
#             import re
#             if self.media_type == 'photo':
#                 capturedate = extract_metadata(self, attr_list=['create_date', 'file_modification_date/time'])
#             elif self.media_type == 'video':
#                 capturedate = extract_metadata(self, attr_list=['file_modification_date/time', 'create_date'])
#             capturedate = re.sub(r'(.*?)(\s+)(.*)', r'\1', capturedate)
#             capturedate = capturedate.replace(':', '')
#             return capturedate
#         def extract_capturetime(self):
#             import re
#             capturetime = extract_metadata(self, attr_list=['create_date', 'file_modification_date/time'])
#             capturetime = capturetime.replace(':', '')
#             capturetime = re.sub(r'(.*?)(\s+)(.*)', r'\3', capturetime)[0:6]
#             return capturetime
#         def extract_seqnum(self):
#             import re
#             # Final sequence of digitis before EOS
#             seqnum = re.sub(r'(.*?)(\d+)(\.\w{3})$', r'\2', self.fname)
#             seqnum = '' if seqnum == self.fname else seqnum
#             return seqnum
#         def extract_cameramodel(self, ns.vol_source_type):
#             cameramodel = extract_metadata(self, attr_list=['camera_model_name', 'device_model_name', 'model', 'compressor_name'])
#             if cameramodel == '{}':
#                 if ns.vol_source_type.lower() == 'dji':
#                     cameramodel = 'FC2103'
#             cameramodel = 'FC220' if cameramodel == 'FC220-Se' else cameramodel
#             cameramodel = 'HERO5 Black' if 'gopro' in cameramodel.lower() else cameramodel
#             return cameramodel
#         # Extract attributes from EXIF used regardless of photo or video
#         self.cd = extract_capturedate(self)
#         self.ct = extract_capturetime(self)
#         self.cm = extract_cameramodel(self, ns.vol_source_type)
#         self.sn = extract_seqnum(self)
#         self.ext = os.path.splitext(self.fname)[1].lower()
#         self.initials = initials
#         # Build new filename
#         if self.media_type == 'photo':
#             newfname = "{}{}{}_{}_{}{}".format(
#                 self.cd, self.initials, self.ct, self.cm, self.sn, self.ext)
#         elif self.media_type == 'video':
#             self.vq = extract_videoquality(self)
#             self.vfr = extract_videoframerate(self)
#             newfname = "{}{}{}_{}_{}_Q{}{}FPS{}".format(
#                 self.cd, self.initials, self.ct, self.cm, self.sn, self.vq, self.vfr, self.ext)
#         else:
#             echo("Unrecognized media_type parameter, must be either 'photo' or 'video'", abort=True)
#         self.newfname = os.path.basename(os.path.join(os.path.dirname(self.fname), newfname))

# def define_params():
#     today          = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
#     var            = Attribute()
#     var.dir        = Attribute()
#     var.vol        = Attribute()
#     var.convention = Attribute()
#     var.app        = Attribute()
#     var.ext        = Attribute()
#     var.vol.source = join('/', 'Volumes', 'PHOTOS1')
#     # Directory parameters
#     var.dir.home      = expanduser('~')
#     var.dir.trash     = join(var.vol.source, '.Trashes', '%s-Photos-Convert-Raw' % today)
#     # var.dir.script    = dirname(realpath(__file__))
#     var.dir.photos    = join(var.vol.source, 'Photos', '_All_Photos')
#     var.dir.git_doni  = join(var.dir.home, 'GDrive', 'Programming', 'Git-Doni')
#     # Application parameters
#     var.app.adobe_dng = join('/', 'Applications', 'Adobe DNG Converter.app',
#         'Contents', 'MacOS', 'Adobe DNG Converter')
#     # Set file naming convention regex
#     convention_base = ''                   +\
#         r'(?P<year>\d{4})'                 +\
#         r'(?P<month>\d{2})'                +\
#         r'(?P<day>\d{2})'                  +\
#         r'(?P<initials>[A-Za-z]{2})'       +\
#         r'(?P<hours>\d{2})'                +\
#         r'(?P<minutes>\d{2})'              +\
#         r'(?P<seconds>\d{2})'
#     var.convention.photo = convention_base               +\
#         '_'                                              +\
#         r'(?P<camera>.*?)'                               +\
#         '_'                                              +\
#         r'(?P<seqnum>(\d{4,}|\d+-\d|-\d|))'              +\
#         r'(?P<affix>(-HDR-*\d*|-Pano-*\d*|-Edit-*\d*|))' +\
#         r'(?P<ext>\.[a-z0-9]{3})'
#     var.convention.video = convention_base +\
#         '_'                                +\
#         r'(?P<camera>.*?)'                 +\
#         '_'                                +\
#         r'(?P<seqnum>.*(\d+))'             +\
#         '_'                                +\
#         r'(?P<quality>Q\d+(K|P))'          +\
#         r'(?P<fps>\d{2,3}FPS)'             +\
#         r'(?P<ext>\.[a-z0-9]{3})'
#     # File extension definitions
#     var.ext.photo = ['jpg', 'dng', 'arw', 'cr2']
#     var.ext.video = ['mov', 'mp4', 'mts', 'm4v', 'avi']
#     var.ext.rm = ['xml', 'lrv', 'wav', 'thm']
#     return var

# def check_params(var):
#     """
#     Print all parameters to screen in YAML-like formatted sequence.

#     Arguments:
#         var {Attribute} -- program variables
#     """

#     echo('Checking parameters from define_params()...', sleep=.2, fg='blue')
#     echo('Directory : Home : {} {}'.format(var.dir.home,
#         emojize(':white_check_mark:', use_aliases=True) if isdir(var.dir.home) else emojize(':x:',
#             use_aliases=True)), sleep=.2)
#     echo('Directory : Trash : {} {}'.format(var.dir.trash,
#         emojize(':white_check_mark:', use_aliases=True) if isdir(dirname(var.dir.home)) else emojize(':x:',
#             use_aliases=True)), sleep=.2)
#     echo('Directory : Photos : {} {}'.format(var.dir.photos,
#         emojize(':white_check_mark:', use_aliases=True) if isdir(var.dir.photos) else emojize(':x:',
#             use_aliases=True)), sleep=.2)
#     echo('Directory : Git Doni : {} {}'.format(var.dir.git_doni,
#         emojize(':white_check_mark:', use_aliases=True) if isdir(var.dir.git_doni) else emojize(':x:',
#             use_aliases=True)), sleep=.2)
#     echo('Application : Adobe DNG : {} {}'.format(
#         var.app.adobe_dng,
#         emojize(':white_check_mark:', use_aliases=True) \
#         if isfile(var.app.adobe_dng) \
#         else emojize(':x:', use_aliases=True)), sleep=.2)
#     echo('Naming Convention : Photo : {} \n{}'.format(
#         emojize(':white_check_mark:', use_aliases=True),
#         '\n'.join(['  ' + click.style(x, fg='cyan') \
#             for x in re.findall(r'\(.*?\)', var.convention.photo)])), sleep=.2)
#     echo('Naming Convention : Video : {} \n{}'.format(
#         emojize(':white_check_mark:', use_aliases=True),
#         '\n'.join(['  ' + click.style(x, fg='cyan') \
#             for x in re.findall(r'\(.*?\)', var.convention.video)])), sleep=.2)
#     echo('File Extension : Photo     : {} {}'.format(
#         ', '.join(var.ext.photo),
#         emojize(':white_check_mark:', use_aliases=True)), sleep=.2)
#     echo('File Extension : Video     : {} {}'.format(
#         ', '.join(var.ext.video),
#         emojize(':white_check_mark:', use_aliases=True)), sleep=.2)
#     echo('File Extension : To Remove : {} {}'.format(
#         ', '.join(var.ext.rm),
#         emojize(':white_check_mark:', use_aliases=True)), sleep=.2)

# def get_master_df(source_files, ext_photo, ext_video, vol_source_type, initials, files_all_in_year):
#     """Build new filename for every source file and return in dataframe with columns:
#     'sourcename', 'destname', 'media_type', 'camera_model', 'capture_date', 'exists'"""
#     import pandas as pd
#     from os.path import basename, splitext
#     from tqdm import tqdm
#     #
#     # Initialize dataframe
#     master = pd.DataFrame(columns=['sourcename', 'destname', 'media_type', 'camera_model', 'capture_date', 'exists'])
#     #
#     # Loop over each file and append a row to 'master' dataframe
#     for fname in tqdm(source_files):
#         #
#         # Initialize MediaFile class for this filename and run 'exiftool'
#         mediafile = MediaFile(fname, ext_photo, ext_video)
#         mediafile.run_exiftool()
#         #
#         # Build new filename from EXIF metadata
#         mediafile.build_fname(initials, ns.vol_source_type)
#         #
#         # Format capture date as YYYY-MM-DD
#         cd_fmt = mediafile.cd[0:4] + '-' + mediafile.cd[4:6] + '-' + mediafile.cd[6:8]
#         #
#         # Check if file already exists anywhere in current year
#         files_in_year = [basename(x).lower() for x in files_all_in_year]
#         exists = any([
#             # Original filename exists in dest year
#             basename(mediafile.fname).lower() in files_in_year,
#             # New filename exists in dest year
#             basename(mediafile.newfname).lower() in files_in_year,
#             # Original filename with .arw extension exists in .dng form in dest year
#             splitext(basename(mediafile.fname))[0].lower() + '.dng' in files_in_year,
#             # New filename with .arw extension exists in .dng form in dest year
#             splitext(basename(mediafile.newfname))[0].lower() + '.dng' in files_in_year
#         ])
#         #
#         # Append row to DF
#         master.loc[len(master)] = [
#             fname,
#             mediafile.newfname,
#             mediafile.media_type,
#             mediafile.cm,
#             cd_fmt,
#             exists
#         ]
#     return master

# def get_dates_to_transfer(master):
#     """Analyze 'master' dataframe, and extract unique dates. For each date, get the number of
#     files with that date already in dest.files.all_in_year. Print all dates to screen using
#     user_select_from_list(), and if there is a file with that date and camera model in
#     dest.files.all_in_year, then indicate that that date has already been dumped. If there are
#     no files with that date/camera model combination in dest.files.all_in_year, then indicate
#     that that date has not yet been dumped."""
#     import pandas as pd, re, click
#     from emoji import emojize
#     from pydoni.pyobj import user_select_from_list
#     #
#     # Get aggregated dataframe of how many source files exist in dest year for each combination
#     # of capture date, camera model and exists
#     datedf = master \
#         .groupby(['capture_date', 'camera_model', 'exists']) \
#         .size() \
#         .reset_index(name='count')
#     datedf = datedf[['capture_date', 'camera_model', 'exists']] \
#         .groupby(['capture_date', 'camera_model']) \
#         .agg('sum') \
#         .reset_index()
#     #
#     # Create custom strings to print to STDOUT to prompt for user input
#     lst = []
#     for idx, row in datedf.iterrows():
#         color = 'green' if row['exists'] else 'red'
#         lst.append('{} {} {}'.format(
#             click.style(str(row['capture_date']), fg=color),
#             click.style('Already dumped!' if color=='green' else 'Not yet dumped!', fg=color),
#             emojize(':white_check_mark:' if color=='green' else ':x:', use_aliases=True)))
#     #
#     # Prompt user to select dates
#     date = user_select_from_list(lst, allow_range=True, indent=1, msg='Please select a date (hyphen-separated range ok)')
#     date = [date] if isinstance(date, str) else date
#     #
#     # Extract dates from strings created in 'lst'
#     date = [re.sub(r'.*(\d{4}-\d{2}-\d{2}).*', r'\1', x) for x in date]
#     return date


# if __name__ == '__main__':
#     main()
