"""
Script name: Dump SD
Script author: Andoni Sooklaris
Date: 2019-01-08
Updated:
    - 2019-09-23
    - 2019-02-19

This program is broken down into three steps:

    (1) Dump
        Prompt user to select a source SD card volume, and a target directory.
        All files on the SD card but not in the target directory will be copied to the
        target directory.
    (2) Rename
        Prompt the user to select a directory containing photo and video files. Any file
        in that directory and its subdirectories will be renamed according to a file naming
        convention established in this program as:

        Photos:
        {Capture Date}{Initials}{Capture Time}_{Camera Model}_{Sequence Number}.{File Extension}

        Videos:
        {Capture Date}{Initials}{Capture Time}_{Camera Model}_{Sequence Number}_Q{Video Quality}{Frame Rate}FPS.{File Extension}

        If files do not match the above convention, they will be renamed. If files already comply
        with the above convention, they will be left alone. The information required by
        this convention must be queried from each file's EXIF metadata using the
        `exiftool` command-line utility.
    (3) Convert
        Run Adobe DNG Converter on a directory containing .arw files and delete the original
        files.

Script arguments:
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

Sample program call:

python DumpSD.py --vol_source='A7R2' --coll_target="/Volumes/PHOTOS1/Photos/_All_Photos/2019/30 September" --date="today" --rename --convert --notify
"""

import argparse
from pydoni.scripts.dump_sd.dump_sd import DumpSD


def initialize_argparser():
    """
    Initiate program argument parser.

    Returns:
        Namespace
    """

    parser = argparse.ArgumentParser(description='Program argument parser')
    parser._action_groups.pop()

    required = parser.add_argument_group('required arguments')
    required.add_argument('--vol_source',type=str, required=True,
        help='Source volume name')
    required.add_argument('--coll_target', type=str, required=True,
        help='Absolute filepath to target collection directory')
    required.add_argument('--date', type=str, required=True,
        help='Date of photos and videos to dump in format YYYY-MM-DD, may enter keywords "today" or "yesterday"')

    optional = parser.add_argument_group('optional arguments')
    optional.add_argument('--rename', action="store_true", default=False,
        help='Run RenameConvert program after files are dumped, rename files (default: {False})')
    optional.add_argument('--convert', action="store_true", default=False,
        help='Run RenameConvert program after files are dumped, convert ARW files to DNG (default: {False})')
    optional.add_argument('--verbose', action="store_true", default=False,
        help='Print program messages to STDOUT (default: {False})')
    optional.add_argument('--notify', action="store_true", default=False,
        help='Send macOS notification upon program completion (default: {False})')
    optional.add_argument('--test_mode', action="store_true", default=False,
        help='Run program in test mode (default: {False})')
    optional.add_argument('--rc_initials', type=str, required=False, default='AS',
        help='Only necessary if `rename_convert` is True. Two-character initials string to insert into new mediafile names (default: {AS})')
    optional.add_argument('--rc_tz_adjust', type=int, required=False, default=0,
        help='subtract this many hours from photo created date to use in file renaming (default: {0})')

    return parser.parse_args()


ns = initialize_argparser()
DumpSD(
    vol_source=ns.vol_source,
    coll_target=ns.coll_target,
    date=ns.date,
    rename=ns.rename,
    convert=ns.convert,
    verbose=ns.verbose,
    notify=ns.notify,
    test_mode=ns.test_mode,
    rc_initials=ns.rc_initials,
    rc_tz_adjust=ns.rc_tz_adjust
).run()
