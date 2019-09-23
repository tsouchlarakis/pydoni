"""

"""

import argparse
from pydoni.scripts.dump_sd.back_up import BackUp


def initialize_argparser():
    """
    Initiate program argument parser.

    Returns:
        Namespace
    """

    parser = argparse.ArgumentParser(description='Program argument parser')
    parser._action_groups.pop()

    required = parser.add_argument_group('required arguments')
    required.add_argument('--source_dir',type=str, required=True,
        help='Absolute path to source directory')
    required.add_argument('--target_dir',type=str, required=True,
        help='Absolute path to target directory')

    optional = parser.add_argument_group('optional arguments')
    optional.add_argument('--prompt', action='store_true', default=False,
        help='Verify with user before executing program (default: {False})')
    optional.add_argument('--skip_copy', action='store_true', default=False,
        help='Skip "copy" portion of program (default: {False})')
    optional.add_argument('--skip_replace', action='store_true', default=False,
        help='Skip "replace" portion of program (default: {False})')
    optional.add_argument('--skip_delete', action='store_true', default=False,
        help='Skip "delete" portion of program (default: {False})')
    optional.add_argument('--logfile', type=str, default=None, required=False,
        help='Log changes to target folder in this file (default: {None})')
    optional.add_argument('--verbose', action='store_true', default=False,
        help='Print program messages to STDOUT (default: {False})')
    optional.add_argument('--notify', action='store_true', default=False,
        help='Send macOS notification on program completion (default: {False})')

    return parser.parse_args()


ns = initialize_argparser()

BackUp(
    source_dir=ns.source_dir,
    target_dir=ns.target_dir,
    prompt=ns.prompt,
    skip_copy=ns.skip_copy,
    skip_replace=ns.skip_replace,
    skip_delete=ns.skip_delete,
    logfile=ns.logfile,
    verbose=ns.verbose,
    notify=ns.notify
).run()
