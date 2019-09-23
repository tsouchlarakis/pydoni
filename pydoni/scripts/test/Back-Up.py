"""-------------------------------------------------------------------------------------------------
Script Name: Back Up
Script Author: Andoni Sooklaris
Date: 2019-01-29

This script will accept a source and target directories, most often on separate external hard
drives, and copy all files from the source to the target that are either:

    (1) Not in the target directory
    (2) Are in the target directory, but have been updated

Files in the target that have been deleted in the source will also be deleted.
-------------------------------------------------------------------------------------------------"""

import re
import time
import click
from tqdm import tqdm
from shutil import copy2
from send2trash import send2trash
from os import stat, makedirs, rename
from os.path import isfile, dirname, join, getmtime, basename, isdir
from pydoni.os import listfiles, macos_notify
from pydoni.vb import echo, verbose_header, clickfmt, program_complete
from pydoni.pyobj import human_filesize, systime, sysdate


def verify_program_execution(fnames, prompt_flag):
    """
    Given all files to copy, replace, delete and leave unchanged, print a summary to
    STDOUT and verify with the user that they would like to proceed with execution.
    
    Arguments:
        fnames {dict} -- with items as lists: 's', 'c', 'r', 'd', 'u' (source/copy/rename/delete/unchanged)
        prompt_flag {bool} -- simply the `prompt` click variable defined at top of
    
    Returns:
        {bool} -- True if program should proceed, False otherwise
    """
    
    assert isinstance(fnames, dict)
    for item in ['s', 'c', 'r', 'd', 'u']:
        assert item in fnames.keys()
    assert isinstance(prompt_flag, bool)

    echo('')
    echo('Total files: {}'.format(
        clickfmt(str(len(fnames['s'])), 'numeric')
    ), fg='white', underline=True, bold=True)
    
    if len(fnames['c']):
        echo('{} {} new source files to target'.format(
            click.style('COPYING  :', fg='green', bold=True),
            click.style(str(len(fnames['c'])).rjust(5), fg='green')
        ), indent=2)
    
    if len(fnames['r']):
        echo('{} {} target files with newer source files'.format(
            click.style('REPLACING:', fg='blue', bold=True),
            click.style(str(len(fnames['r'])).rjust(5), fg='blue')
        ), indent=2)
    
    if len(fnames['d']):
        echo('{} {} target files that have since been removed from source'.format(
            click.style('DELETING :', fg='red', bold=True),
            click.style(str(len(fnames['d'])).rjust(5), fg='red')
        ), indent=2)
    
    if len(fnames['u']):
        echo('{} {} source files will not be transferred'.format(
            click.style('UNCHANGED:', fg='yellow', bold=True),
            click.style(str(len(fnames['u'])).rjust(5), fg='yellow')
        ), indent=2)
    
    echo('')
    
    if prompt_flag:
        return click.confirm('Proceed with program execution?')
    else:
        return True


def execute(fnames, runtype, source_drive, target_drive, log, program_log, verbose):
    """
    Copy, replace or delete files at target.
    
    Arguments:
        fnames {list} -- list of files to operate on
        runtype {str} -- one of 'c', 'r' or 'd' (copy/replace/delete)
        source_drive {str} -- source drive name
        target_drive {str} -- target drive name
        log {bool} -- if True, add to program log
        program_log {ProgramLog} -- ProgramLog instance
        verbose {bool} -- print messages to STDOUT

    Returns:
        {bool} -- True if run successfully
    """

    assert isinstance(fnames, list)
    assert isinstance(runtype, str)
    assert isinstance(source_drive, str)
    assert isinstance(target_drive, str)
    assert isinstance(log, bool)


    def execute_file(fname, source_drive, target_drive, runtype):
        fsize = stat(fname).st_size
        
        try:    
            fsize_h = human_filesize(fsize)
        except:
            fsize_h = 'NA'
        
        fname_target = fname.replace(source_drive, target_drive)
        
        if runtype == 'c':
            dname = dirname(fname_target)
            if not isdir(dname):
                makedirs(dname)
            if isfile(fname):
                copy2(fname, fname_target)
        elif runtype == 'r':
            if isfile(fname):
                copy2(fname, fname_target)    
        elif runtype == 'd':
            if isfile(fname):
                send2trash(fname)


    # Item(s) for verbose output
    if runtype == 'c':
        gerund = 'copying'
    elif runtype == 'r':
        gerund = 'replacing'
    elif runtype == 'd':
        gerund = 'deleting'

    # Get total filesize of files to operate on and print verbose header
    total_fsize = sum([stat(x).st_size for x in fnames if isfile(x)])
    if verbose:
        verbose_header('{} {} files to target (Total filesize: {})'.format(
            gerund.capitalize(),
            str(len(fnames)),
            human_filesize(total_fsize)))
       
        with tqdm(total=total_fsize, unit='B', unit_scale=True, unit_divisor=1024) as pbar:
            for fname in fnames:
                pbar.set_postfix(file=fname[-14:], fsize=fsize_h, refresh=False)
                execute_file(fname, source_drive, target_drive, runtype)
                pbar.update(fsize)  
                if log is True:
                    program_log.append_entry(fname=fname, runtype=runtype)
    else:
        for fname in fnames:
            execute_file(fname, source_drive, target_drive, runtype)

    return True
    

def add_line_last_update_yaml(fname, mode, indent=2):
    """
    Add entry to 'Last-Update.yaml' if it exists.
    
    Arguments:
        fname {str} -- path to 'Last-Update.yaml'
        mode {str} -- one of 'books', 'movies', 'music', 'photos'

    Keyword Arguments:
        indent {int} -- size of YAML indent (default: 2)

    Returns:
        nothing
    """

    assert isinstance(fname, str)
    assert isfile(fname)
    assert isinstance(mode, str)
    assert mode in ['books', 'movies', 'music', 'photos']
    assert isinstance(indent, int)

    with open(fname, 'r') as f:
        text = f.readlines()
    
    # Get index to insert date at
    ins = None
    for i, line in enumerate(text):
        if line.strip().lower().replace(':', '') == mode:
            ins = i + 1

    # Write today's date at position `ins` if found in list
    if ins is not None:
        outtext = text[0:ins] + [' '*indent + '- ' + sysdate() + '\n'] + text[ins:]
    
    # Overwrite output file
    if isinstance(outtext, list):
        if len(outtext) > 0:
            with open(fname, 'w') as f:
                for line in outtext:
                    f.write(line)


class BackUp(object):
    """
    Back up one directory to another.
    """
    def __init__(
        self,
        source_dir,
        target_dir,
        prompt,
        skip_copy,
        skip_replace,
        skip_delete,
        logfile,
        verbose,
        notify
        ):
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.prompt = prompt
        self.skip_copy = skip_copy
        self.skip_replace = skip_replace
        self.skip_delete = skip_delete
        self.logfile = logfile
        self.log = True if isinstance(self.logfile, str) else False
        self.verbose = verbose
        self.notify = notify

        # Files scanned must be either replaced, copied, deleted or left unchanged
        self.file = dict(
            unchanged = [],
            replace   = [], # Source file different date modified than target file
            copy      = [], # Target file does not yet exist
            delete    = []  # Source file deleted but still present in target
        )

        # Copy/delete speeds
        # self.copy_speed = 37095125.81813995  # Bytes/second
        # self.delete_speed = 9388824000  # Bytes/second

        # File metadata attribute to compare creation times
        self.attr_dm = 'File Modification Date/Time'

        # Parse source and target drive names
        self.source_drive = '/'.join(source_dir.split('/')[0:2])
        self.target_drive = '/'.join(target_dir.split('/')[0:2])

    def run():
        """
        Execute backup.
        """

        assert isdir(self.source_dir)
        assert isdir(self.target_dir)
        assert isdir(self.source_drive)
        assert isdir(self.target_drive)

        if self.verbose:
            start_time = time.time()

        if self.log:
            if not isfile(self.logfile):
                with open(self.logfile, 'w') as f:
                    columns = ['date_logged','action','source_dir','dest_dir','fname']
                    columns = '"' + '","'.join(columns) + '"'
                    f.write(columns + '\n')

            log = ProgramLog(
                logfile=self.logfile,
                source_dir=self.source_dir,
                target_dir=self.target_dir)

        # # Directory parameters
        # var.dir.home     = expanduser('~')
        # var.dir.script   = dirname(realpath(__file__))
        # self.logfile     = join(var.dir.script, 'data', 'Back-Up-Log.csv')
        # var.dir.git_doni = join(var.dir.home, 'GDrive', 'Programming', 'Git-Doni')
        # var.drive.root   = join('/', 'Volumes')
        
        # Get source and target files
        fnames_source = listfiles(path=self.source_dir, recursive=True, full_names=True)
        fnames_target = listfiles(path=self.target_dir, recursive=True, full_names=True)
        

        # Loop over every file and compare modification dates to determine which files to copy to target
        # sec_it = 0.0005  # Approx. 2000 iterations per second
        if self.verbose:
            verbose_header('Scanning all source and target files')
            iterable = tqdm(fnames_source, unit='file')
        else:
            iterable = fnames_source
        
        for fname_source in iterable:
            fname_target = fname_source.replace(self.source_drive, self.target_drive)
            
            if isfile(fname_target):
                if getmtime(fname_source) == getmtime(fname_target):
                    if stat(fname_source).st_size == stat(fname_target).st_size:
                        self.file['unchanged'].append(fname_source)
                        continue
                self.file['replace'].append(fname_source)
            else:
                self.file['copy'].append(fname_source)

        # Get files to delete: those in target that have since been removed from source
        for fname_target in fnames_target:
            fname_source = fname_target.replace(self.target_drive, self.source_drive)
            if not isfile(fname_source):
                self.file['delete'].append(fname_target)

        # Ask user for final confirmation before proceeding, if specified with 'prompt' param,
        # otherwise print what changes will take place and proceed automatically
        fnames_source_dict = dict(
            s = fnames_source,
            r = self.file['replace'],
            c = self.file['copy'],
            d = self.file['delete'],
            u = self.file['unchanged'])
        if not verify_program_execution(fnames=fnames_source_dict, prompt_flag=self.prompt):
            echo('Must answer affirmatively!', abort=True)

        # Add single newline to log
        if self.log:
            if len(self.file['copy']) or len(self.file['replace']) or len(self.file['delete']):
                with open(log.logfile, 'a') as f:
                    f.write('\n')
        
        # Copy files to target
        if not self.skip_copy:
            if len(self.file['copy']):
                execute(
                    fnames       = self.file['copy'],
                    runtype      = 'c',
                    source_drive = self.source_drive,
                    target_drive = self.target_drive,
                    program_log  = log,
                )
                echo('')

        # Replace files at target
        if not self.skip_replace:
            if len(self.file['replace']):
                # 392498242564 file size in 10580 seconds (2.9391 hours)
                execute(
                    fnames       = self.file['replace'],
                    runtype      = 'r',
                    source_drive = self.source_drive,
                    target_drive = self.target_drive,
                    program_log  = log,
                )
                echo('')
        
        # Delete files at target
        if not self.skip_delete:
            if len(self.file['delete']):
                execute(
                    fnames       = self.file['delete'],
                    runtype      = 'd',
                    source_drive = self.source_drive,
                    target_drive = self.target_drive,
                    program_log  = log,
                )
                echo('')

        # Update 'Last-Update.yaml' if it exists
        last_update_yaml = join(self.target_drive, 'Last-Update.yaml')
        if isfile(last_update_yaml):
            
            mode = None
            if basename(self.target_dir).lower() == 'books':
                mode = 'books'
            elif basename(self.target_dir).lower() == 'movies':
                mode = 'movies'
            elif basename(self.target_dir).lower() == 'music':
                mode = 'music'
            elif basename(self.target_dir).lower() == 'photos':
                mode = 'photos'
            
            if mode is not None:
                add_line_last_update_yaml(fname=last_update_yaml, mode=mode)

        if verbose:
            program_complete(start_time=start_time, end_time=time.time())

        if notify:
            content_image = '/Users/Andoni/GDrive/Code/git-doni/photos/back-up/img/back-up-icon.png'
            content_image = content_image if isfile(content_image) else None
            macos_notify(title='Back Up', message='Back up completed successfully!',
                content_image=content_image)


class ProgramLog(object):
    
    def __init__(self, logfile, source_dir, target_dir):
        
        assert isinstance(logfile, str)
        assert isdir(source_dir)
        assert isdir(target_dir)

        self.logfile    = logfile
        self.source_dir = source_dir
        self.target_dir = target_dir
    
    def append_entry(self, fname, runtype):
        """
        Append an entry to logfile
        
        Arguments:
            fname {str} -- filename to append in log entry
            runtype {str} -- one of 'c', 'r' or 'd' (copy/replace/delete)
        """

        assert isinstance(fname, str)
        assert isinstance(runtype, str)
        assert runtype in ['c', 'r', 'd']

        # Make logfile if doesn't exist
        if not isfile(self.logfile):
            open(self.logfile, 'w')
    
        # Append line to logfile
        assert isfile(self.logfile)
        with open(self.logfile, 'a') as f:
            f.write('"{}","{}","{}","{}","{}"\n'.format(
                systime(),
                runtype,
                self.source_dir,
                self.target_dir,
                fname
            ))

