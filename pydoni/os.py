import pydoni
import pydoni.sh


class FinderMacOS(object):
    """
    MacOS Finder object. Holds functions to carry out Finder operations on a file or directory.

    :param fpath: path to file or directory to operate on
    :type fpath: str
    """

    def __init__(self):

        self.bin_mdls = pydoni.sh.find_binary('mdls')
        self.bin_mdls_osa = pydoni.sh.find_binary('osascript')

        self.logger = pydoni.logger_setup(
            name=pydoni.what_is_my_name(classname=self.__class__.__name__, with_modname=True),
            level=pydoni.modloglev)

        self.logger.info('Initialized FinderMacOS object')

        if self.bin_mdls is not None:
            self.logger.info('mdls binary found: ' + self.bin_mdls)
        else:
            self.logger.warning("No 'mdls' binary found")

        if self.bin_mdls is not None:
            self.logger.info('osascript binary found: ' + self.bin_osa)
        else:
            self.logger.warning("No 'osascript' binary found")

    def get_comment(self, fpath):
        """
        Call `mdls` BASH command to retrieve a file's Finder comment on macOS.

        :param fpath: path to file to operate on
        :type fpath: str
        :return: file's comment
        :rtype: str
        """
        self.logger.info('Getting comment from file: ' + fpath)

        cmd = '%s -r -nullMarker "" -n kMDItemFinderComment "%s"' % (self.bin_mdls, fpath)
        self.logger.var('cmd', cmd)

        res = pydoni.syscmd(cmd, encoding='utf-8')
        self.logger.var('res', res)

        if 'could not find ' + basename(fpath) in res:
            self.logger.error('Could not find Finder comment')
            res = ''

        return res

    def write_comment(self, fpath, comment):
        """
        Use Applescript to write a Finder comment to a file.

        :param fpath: path to file to operate on
        :type fpath: str
        :param comment: comment string to write to file
        :type comment: str
        :return: True if successful, False otherwise
        :rtype: bool
        """
        self.logger.info("Setting comment '%s' on file: %s" % (comment, fpath))

        cmd = '%s -e' % self.bin_osa
        self.logger.var('cmd', cmd)

        applescript = '\n'.join([
            'set filepath to POSIX file "{file}"',
            'set the_file to filepath as alias',
            'tell application "Finder" to set the comment of the_file to "{comment}"'
        ])
        self.logger.var('applescript', applescripdt)

        applescript_clear = applescript.format(file=fpath, comment='test')
        applescript_set = applescript.format(file=fpath, comment=comment)

        applescript_clear = re.sub(r'"', r'\"', applescript_clear)
        applescript_set = re.sub(r'"', r'\"', applescript_set)

        self.logger.var('applescript_clear', applescript_clear)
        self.logger.var('applescript_set', applescript_set)

        try:
            cmd_exec_clear = cmd + ' "' + applescript_clear + '"'
            self.logger.var('cmd_exec_clear', cmd_exec_clear)
            pydoni.syscmd(cmd_exec_clear)

            cmd_exec_set = cmd + ' "' + applescript_set + '"'
            self.logger.var('cmd_exec_set', cmd_exec_set)
            pydoni.syscmd(cmd_exec_set)

            return True

        except Exception as e:
            self.logger.excption('Setting Finder comment failed')
            self.logger.debug(str(e))
            return False

    def remove_comment(self, fpath):
        """
        Use Applescript to remove a file's Finder comment.

        :param fpath: path to file to operate on
        :type fpath: str
        :return: True if successful, False otherwise
        :rtype: bool
        """
        self.logger.info('Removing comment from file: ' + fpath)

        cmd = '%s -e' % self.bin_osa
        self.logger.var('cmd', cmd)

        applescript = '\n'.join([
            'set filepath to POSIX file "{file}"',
            'set the_file to filepath as alias',
            'tell application "Finder" to set the comment of the_file to "{comment}"'
        ])
        applescript = re.sub(r'"', r'\"', applescript)
        self.logger.var('applescript', applescripdt)

        try:
            cmd_exec = cmd + ' "' + applescript + '"'
            self.logger.var('cmd_exec', cmd_exec)
            os.system(cmd_exec)

            return True

        except Exception as e:
            self.logger.excption('Removing Finder comment failed')
            self.logger.debug(str(e))
            return False

    def get_tag(self, fpath):
        """
        Parse `mdls` output to get a file's Finder tags.

        :param fpath: path to file to operate on
        :type fpath: str
        :return: list of Finder tags on file
        :rtype: list
        """
        self.logger.info('Getting tags from file: ' + fpath)

        cmd = '%s -r -nullMarker "" -n kMDItemUserTags "%s"' % (self.bin_mdls, fpath)
        self.logger.var('cmd', cmd)

        tags = str(pydoni.syscmd(cmd, encoding='utf-8'))

        if tags == '0':
            self.logger.warning('No tags found for file: ' + fpath)
            return []

        tags = [x.strip() for x in tags.split('\n') if '(' not in x and ')' not in x]
        tags = [x.replace(',', '') for x in tags]
        tags = pydoni.ensurelist(tags)
        self.logger.var('tags', tags)

        return tags

    def write_tag(self, tag):
        """
        Write Finder tag or tags to a file. Requires Jdberry's 'tag' command line utility to
        be installed. Install here: https://github.com/jdberry/tag

        Arguments:
            tag {str} or {list} -- string or list of finder tags. Usually one or more of 'Red', 'Orange', 'Yellow', ...

        Returns:
            {bool}
        """
        tag = [tag] if isinstance(tag, str) else tag
        res = []
        for tg in tag:
            z = pydoni.syscmd('tag --add "%s" "%s"' % (tg, fpath))
            res.append(z)
        if len(list(set(res))) == 1:
            if list(set(res)) == [0]:
                return True
            else:
                return False
        else:
            return False

    def remove_tag(self, tag):
        """
        Remove a Finder tag or tags from a file. Requires Jdberry's 'tag' command line utility to
        be installed. Install here: https://github.com/jdberry/tag

        Arguments:
            tag {str} or {list} -- name(s) of Finder tags to remove

        Returns:
            {bool}
        """

        if tag == 'all':
            tag = self.get_tag()
        elif isinstance(tag, str):
            tag = [tag]

        res = []
        for tg in tag:
            z = pydoni.syscmd('tag --remove "%s" "%s"' % (tg, fpath))
            res.append(z)

        if len(list(set(res))) == 1:
            if list(set(res)) == [0]:
                return True
            else:
                return False
        else:
            return False


class TMBackup(object):

    def __init__(self):

        self.bin = pydoni.sh.find_binary('tmutil')

        self.logger = pydoni.logger_setup(
            name=pydoni.what_is_my_name(classname=self.__class__.__name__, with_modname=True),
            level=pydoni.modloglev)

        self.logger.info('Initialized TMBackup object on binary: %s' % self.bin)

    def parse_latestbackup(self):
        """
        Get last update and last drive from tmutil latestbackup command.

        :return: (drive name, last TM backup date)
        :rtype: tuple
        """
        out = pydoni.syscmd('%s latestbackup' % self.bin).decode('utf-8').strip()

        try:
            lastdate = basename(out)
            lastdate = datetime.strptime(lastdate, '%Y-%m-%d-%H%M%S')
            lastdate = lastdate.strftime('%Y-%m-%d %H:%M:%S')
            lastdrive = out.split('/Backups.backupdb')[0]

            self.logger.var('lastdrive', lastdrive)
            self.logger.var('lastdate', lastdate)

            return (lastdrive, lastdate)

        except Exception as e:
            self.logger.exception('Failed to parse last drive and backup date')
            self.logger.error(str(e))
            return (None, None)

    def start(self):
        """
        Start Time Machine backup.
        """
        pydoni.syscmd('%s startbackup' % self.bin)
        self.logger.info('Started TM backup')

    def stop(self):
        """
        Stop Time Machine backup.
        """
        pydoni.syscmd('%s stopbackup' % self.bin)
        self.logger.info('Stopped TM backup')

    def log_sql(self, pg_dbname, pg_user, pg_schema='code', pg_table='timemachine'):
        """
        Log last time machine value in Postgres database.

        :param pg_dbname: Postgres database name
        :type pg_dbname: str
        :param: pg_user: Postgres username
        :type pg_user: str
        :param pg_schema: target table to update with columns 'completed_on',
                          'backup_drive', 'checked_at'
        :type pg_schema: str
        :param pg_table: target schema containing `pg_table`
        :type pg_table: str
        """

        pg = Postgres(pg_user=pg_user, pg_dbname=pg_dbname)
        lastdrive, lastdate = self.parse_latestbackup()

        if lastdrive is not None and lastdate is not None:
            sql = pg.build_insert(
                schema=pg_schema,
                table=pg_table,
                columns=['completed_on', 'backup_drive', 'checked_at'],
                values=[lastdate, lastdrive, datetime.now()])
            pg.execute(sql)
            self.logger.info("Inserted record to {}.{}".format(pg_schema, pg_table))


def assert_dpath(dpaths=[], abort=True):
    """
    Check that a given path or paths exist. Optional abort program if one or more directories
    do not exist.

    :param dpaths: directory path(s) to check for existence
    :type dpaths: str or list
    :param abort: execute `quit()` if one or more directories do not exist
    :type abort: bool
    :return: True if all directories exist, False otherwise
    :rtype bool:
    """

    import os

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    dpaths = [expanduser(x) for x in pydoni.ensurelist(dpaths)]
    res = [(d, os.path.isdir(d)) for d in dpaths]

    for d, exists in res:
        if not exists:
            logger.error("Directory does not exist: " + d)

    if all([exists for d, exists in res]):
        return True
    else:
        if abort:
            quit()
        else:
            return False


def unarchive(fpath, dest_dir):
    """
    Unpack a .zip archive.

    :param fpath: path to zip archive file
    :type fpath: str
    :param dest_dir: path to destination extract directory
    :type dest_dir: str
    """

    import zipfile

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    with zipfile.ZipFile(fpath, 'r') as zip_ref:
        zip_ref.extractall(dest_dir)


def macos_notify(
        title='',
        subtitle=None,
        message='',
        app_icon=None,
        content_image=None,
        command=None,
        open_iterm=False):
    """
    Python wrapper for julienXX's terminal-notifier gem found here:
        https://github.com/julienXX/terminal-notifier

    :param title: title string for notification
    :type title: str
    :param subtitle: subtitle string for notification
    :type subtitle: str
    :param message: message string for notification
    :type message: str
    :param app_icon: path to image file to display instead of application icon
    :type app_icon: str
    :param content_image: path to image file to attach inside of notification
    :type content_image: str
    :param command: shell command string to execute when notification is clicked
    :type command: str
    :param open_iterm: overwrites 'command' parameter as 'open /Applications/iTerm.app'
    :type open_iterm: bool
    """

    import os

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    bin = pydoni.sh.find_binary('terminal-notifier')
    if not bin:
        error_str = "terminal-notifier is not installed! Please install it per instructions " + \
            "at https://github.com/julienXX/terminal-notifier"
        logger.error(error_str)

    if os.name.lower() != 'posix':
        raise OSError('Operating system not macOS!')

    # Build list of arguments for terminal-notifier and check that each parameter is valid
    cl_string = []
    if title is not None:
        assert isinstance(title, str)
        cl_string.append('-title {!r}'.format(title))

    if subtitle is not None:
        assert isinstance(subtitle, str)
        cl_string.append('-subtitle {!r}'.format(subtitle))

    if message is not None:
        assert isinstance(message, str)
        cl_string.append('-message {!r}'.format(message))

    if app_icon is not None:
        assert isinstance(app_icon, str)
        assert os.path.isfile(app_icon)
        cl_string.append('-appIcon {!r}'.format(app_icon))

    if content_image is not None:
        assert isinstance(content_image, str)
        assert os.path.isfile(content_image)
        cl_string.append('-contentImage {!r}'.format(content_image))

    assert isinstance(open_iterm, bool)

    if open_iterm:
        cl_string.append("-execute 'open /Applications/iTerm.app'")

    elif command is not None:
        assert isinstance(command, str)
        cl_string.append('-execute {!r}'.format(command))

    # Build final command and execute
    cmd = '{} {}'.format(bin, ' '.join(cl_string))
    pydoni.syscmd(cmd)


def find_drives(external_only=False):
    """
    List attached drives, if any.

    :param external_only: filter drive list for only externally attached drives
    :type external_only: bool
    :return: list of attached drives
    :rtype: list
    """

    import os

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    volumes = pydoni.listdirs(os.path.join('/', 'Volumes'), full_names=True)

    if external_only:
        volumes = [v for v in volumes if os.path.basename(v) not in ['Macintosh HD', 'Recovery']]
        volumes = [v for v in volumes if 'com.' not in os.path.basename(v)]

    return volumes


def du_by_filetype(
        dir,
        recursive=False,
        verbose=False,
        human=False,
        progress=False,
        total=True):
    """
    List filesize of directory by filetype.

    :param dir {str} path to directory to check
    :param recursive {bool} list files recursively
    :param verbose {bool} print output dictionary to console
    :param human {bool} display filesize in human-readable format
    :param progress {bool} display TQDM progress bar when scanning files
    :param total {bool} display total filesize of directory as final line
    :return {dict}: dictionary in format {extension: filesyze}
    """

    import os

    if progress:
        from tqdm import tqdm

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)

    owd = os.getcwd()
    logger.logvars(locals())

    os.chdir(dir)
    logger.info("Changed dir to '%s'" % dir)

    logger.info('Listing files%s recursively...' % '' if recursive else ' not')
    files = pydoni.listfiles(recursive=recursive)
    logger.info("Files found: %s" % str(len(files)))
    filexts = list(set([os.path.splitext(f)[1].lower() for f in files]))
    logger.info("File extensions found: %s" % str(filexts))
    extdict = {k: 0 for k in filexts}

    if progress:
        pbar = tqdm(total=len(files), unit='file')

    logger.info("Scanning all files and extracting filesizes")
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        extdict[ext] += os.stat(f).st_size
        if progress:
            pbar.update(1)

    logger.info("Scanning successful")
    if progress:
        pbar.close()

    # Define any extension name replacements. By default, '' is replaced
    # with 'None'
    if '' in extdict.keys():
        extdict['None'] = extdict.pop('')

    # Order dictionary by filesize in descending order
    extdict = {k: v for k, v in \
        sorted(extdict.items(), key=lambda item: item[1], reverse=True)}

    if total:
        extdict['total'] = sum([v for k, v in extdict.items()])
        logger.info("Added 'total' row")

    if human:
        extdict = {k: pydoni.human_filesize(v) for k, v in extdict.items()}
        logger.info("Formatted as human-readable filesizes")

    if verbose:
        logger.info("Printing output to console")
        for ext, sizeb in extdict.items():
            print(ext + ' ' + str(sizeb))

    os.chdir(owd)
    logger.info("Changed directory back to '%s'" % owd)
    return extdict


def excel_to_csv(excel_file, outfile=None):
    """
    Convert an Excel spreadsheet to a CSV file.

    :param excel_file {str} path to excel file to convert
    :param outfile {str} path to output CSV file
    """

    import os
    import pandas as pd

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    if outfile is None:
        outfile = os.path.splitext(excel_file)[0] + '.csv'

    xlsx = pd.ExcelFile(excel_file)
    sheets = xlsx.sheet_names

    logger.logvars(locals())

    if len(sheets) > 1:
        logger.info('Writing multiple sheets')
        for sheet in sheets:
            data_xlsx = pd.read_excel(excel_file, sheet_name=sheet)
            tmpout = os.path.splitext(outfile)[0] + '-' + sheet + '.csv'
            data_xlsx.to_csv(tmpout, encoding='utf-8', index=False)

    else:
        logger.info('Writing single sheets')
        data_xlsx = pd.read_excel(excel_file)
        data_xlsx.to_csv(outfile, encoding='utf-8', index=False)


def delete_empty_dirs(root, recursive=False, true_remove=False, count_hidden_files=True):
    """
    Scan a directory and delete any bottom-level empty directories.

    :param recursive: scan `root` recursively and iterate down the directory tree
    :type recursive: bool
    :param true_remove: delete directories that contain only empty directories
    :type true_remove: bool
    :param count_hidden_files: count hidden files in evaluating whether directory is empty
    :type count_hidden_files: bool
    """

    import os
    import shutil
    from send2trash import send2trash

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())
    logger.info('Scanning for empty bottom-level dirs at: ' + root)

    def scan_dirs(dirs):
        dirs_remove = []

        for dir in dirs:
            fulldir = os.path.join(root, dir)
            files_present = pydoni.listfiles(path=fulldir, include_hidden_files=count_hidden_files)
            dirs_present = pydoni.listdirs(path=fulldir, recursive=False)
            if len(files_present + dirs_present) == 0:
                dirs_remove.append(fulldir)

        return dirs_remove

    dirs_remove = scan_dirs(pydoni.listdirs(path=root, recursive=recursive))

    if not len(dirs_remove):
        logger.warn('No empty dirs found!')

    while len(dirs_remove):
        for dir in dirs_remove:
            try:
                # shutil.rmtree(dir)
                send2trash(dir)
                logger.info('Deleted: ' + dir)
            except Exception as e:
                logger.exception('Could not remove dir: ' + dir)

        if true_remove:
            dirs_remove = scan_dirs(pydoni.listdirs(path=root, recursive=recursive))
        else:
            dirs_remove = []


