"""
Script Name: Rename and Convert
Script Author: Andoni Sooklaris
Date: 2019-03-15
Updated:
    - 2019-09-22
    - 2019-07-05

Rename all photo and video files in a directory, and convert RAW files to DNG if specified.

Script Arguments:
    dname {str} -- directory name to run program on
    initials {str} -- two-character initial string
    tz_adjust {int} -- subtract this many hours from photo created date to use in file renaming (default: {0})
    ignore_rename {bool} -- if True, ignore the Rename portion of program (default: {False})
    ignore_convert {bool} -- if True, ignore the Convert portion of program (default: {False})
    recursive {bool} -- if True, operate on all subdirectories found in `dname` (default: {False})
    verbose {bool} -- if True, print messages to STDOUT (default: {False})

Sample Call:
    python RenameConvert.py --dname="/Volumes/PHOTOS1/.tmp.dumpsd" --initials="AS" --verbose
"""

import argparse
from pydoni.scripts.dump_sd.rename_convert import RenameConvert


def initialize_argparser():
    """
    Initiate program argument parser.

    Returns:
        Namespace
    """

    parser = argparse.ArgumentParser(description='Program argument parser')
    parser._action_groups.pop()

    required = parser.add_argument_group('required arguments')
    required.add_argument('--dname',type=str, required=True,
        help='Directory name to run program on')

    optional = parser.add_argument_group('optional arguments')
    optional.add_argument('--initials', type=str, required=False, default='AS',
        help='Two-character initial string')
    optional.add_argument('--tz_adjust', type=int, required=False, default=0,
        help='Subtract this many hours from photo created date to use in file renaming (default: {False})')
    optional.add_argument('--ignore_rename', action='store_true', default=False,
        help='Ignore the Rename portion of program (default: {False})')
    optional.add_argument('--ignore_convert', action='store_true', default=False,
        help='Ignore the Convert portion of program (default: {False})')
    optional.add_argument('--recursive', action='store_true', default=False,
        help='Operate on all subdirectories found in `dname` (default: {False})')
    optional.add_argument('--verbose', action='store_true', default=False,
        help='Print messages to STDOUT (default: {False})')
    optional.add_argument('--notify', action='store_true', default=False,
        help='Send macOS notification upon program completion (default: {False})')

    return parser.parse_args()


ns = initialize_argparser()
RenameConvert(
    dname=ns.dname,
    initials=ns.initials,
    tz_adjust=ns.tz_adjust,
    ignore_rename=ns.ignore_rename,
    ignore_convert=ns.ignore_convert,
    recursive=ns.recursive,
    verbose=ns.verbose,
    notify=ns.notify
).run()
