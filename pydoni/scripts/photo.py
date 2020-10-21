import pydoni
import pydoni.sh
import pydoni.vb
import pydoni.scripts
from pydoni.scripts.__script_resources__.photo import Convention, Extension, MediaFile


def rename_mediafile(
        file,
        initials='AKS',
        tz_adjust=0,
        verbose=False,
        notify=False):
    """
    Rename a photo or video file according to a specified file naming convention.

    :param file: filename or list of filenames to rename
    :type file: str or list
    :param initials: 2 or 3 letter initials string
    :type initials: str
    :param notify: execute `pydoni.os.macos_notify()` on program completion
    :type notify: bool
    :param tz_adjust: adjust file creation times by a set number of hours
    :type tz_adjust: int
    :param verbose: print messages and progress bar to console
    :type verbose: bool
    """
    pydoni.pydonicli_register({'command_name': pydoni.what_is_my_name(with_modname=True)})
    args, result = pydoni.pydonicli_declare_args(locals()), dict()
    pydoni.pydonicli_register({k: v for k, v in locals().items() if k in ['args', 'result']})

    import os, re, click
    from pydoni.vb import echo
    from tqdm import tqdm

    assert isinstance(initials, str)
    assert len(initials) in [2, 3]
    assert isinstance(tz_adjust, int)
    assert isinstance(verbose, bool)

    def parse_media_type(file_ext, EXT):
        """
        Given a file extension, get the type of media
        One of 'photo', 'video' or 'remove'

        :param file_ext: file extension to parse
        :type file_ext: str
        :param EXT: Extension object
        :type EXT: Extension
        :return: type of media
        :rtype: str
        """

        for attr_name in [x for x in dir(EXT) if not x.startswith('__')]:
            if file_ext in getattr(EXT, attr_name):
                return attr_name

        raise Exception('Invalid extension: ' + str(file_ext))

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    mediafiles = pydoni.ensurelist(file)
    CONV = Convention()
    EXT = Extension()

    mediafiles = [os.path.abspath(x) for x in mediafiles \
        if not re.match(CONV.photo, os.path.basename(x)) \
        and not re.match(CONV.video, os.path.basename(x))]

    msg = 'Renaming %s media files' % str(len(mediafiles))
    logger.info(msg)
    if verbose:
        pydoni.vb.verbose_header(msg)
        pbar = tqdm(total=len(mediafiles), unit='mediafile')

    if not len(mediafiles):
        if verbose:
            echo('No files to rename!', fg='green')

    for mfile in mediafiles:
        if verbose:
            pbar.set_postfix(mediafile=pydoni.vb.stabilize_postfix(mfile, max_len=15))

        mf = MediaFile(mfile)
        newfname = mf.build_fname(initials=initials, tz_adjust=tz_adjust)
        newfname = os.path.join(os.path.dirname(mfile), os.path.basename(newfname))

        if os.path.basename(mfile) != os.path.basename(newfname):
            os.rename(mfile, newfname)
            result[os.path.basename(mfile)] = os.path.basename(newfname)
            if verbose:
                tqdm.write('{}: {} -> {}'.format(
                    click.style('Renamed', fg='green'),
                    os.path.basename(mfile),
                    os.path.basename(newfname)))
        else:
            result[os.path.basename(mfile)] = '<not renamed, new filename identical>'
            if verbose:
                tqdm.write('{}: {}'.format(
                    click.style('Not renamed', fg='red'),
                    os.path.basename(mfile)))

        if verbose:
            pbar.update(1)

    if verbose:
        pbar.close()
        echo('Renamed media files: %s' % str(len(mediafiles)), indent=2)

    if verbose or notify:
        pydoni.os.macos_notify(title='Mediafile Rename', message='Completed successfully!')

    pydoni.pydonicli_register({k: v for k, v in locals().items() if k in ['args', 'result']})


def website_extract_image_titles(website_export_dir, outfile, verbose):
    """
    Scan photo files exported for andonisooklaris.com and construct list of image filenames
    and titles, separated by collection.

    :param website_export_dir:
    :type website_export_dir: str
    :param outfile:
    :type outfile: str
    :param verbose:
    :type verbose: bool
    """
    pydoni.pydonicli_register({'command_name': pydoni.what_is_my_name(with_modname=True)})
    args, result = pydoni.pydonicli_declare_args(locals()), dict()
    pydoni.pydonicli_register({k: v for k, v in locals().items() if k in ['args', 'result']})

    import os
    import pandas as pd
    from tabulate import tabulate

    def echo(*args, **kwargs):
        kwargs['timestamp'] = True
        pydoni.vb.echo(*args, **kwargs)

    if outfile == 'auto':
        outfile = os.path.join(website_export_dir, 'Image Titles %s.txt' % pydoni.sysdate(stripchars=True))
    elif outfile is not None:
        assert not os.path.isfile(outfile)

    files = pydoni.listfiles(path=website_export_dir, recursive=True, full_names=True)
    files = [f for f in files if os.path.splitext(f)[1].lower() != '.txt']

    if verbose:
        echo('Files found: ' + str(len(files)))
        echo('Extracting EXIF metadata...')
        exifd = pydoni.sh.EXIF(files).extract()
        echo('EXIF metadata successfully extracted')

        if outfile is not None:
            echo('Writing output datafile: ' + outfile)
    else:
        exifd = pydoni.sh.EXIF(files).extract()

    i = 0
    tracker = pd.DataFrame(columns=['collection', 'file', 'title'])
    for file in files:
        elements = file.replace(website_export_dir, '').lstrip('/').split('/')
        subcollection = None
        collection = elements[0]
        fname = elements[-1]

        if len(elements) == 3:
            subcollection = elements[1]
            collection += ' - ' + subcollection

        exif = exifd[os.path.join(website_export_dir, file)]
        title = exif['Title'] if 'Title' in exif.keys() else ''
        year = fname[0:4]
        title = str(year) + ' ' + str(title)

        tracker.loc[i] = [collection, fname, title]
        i += 1


    print_lst = []
    for collection in tracker['collection'].unique():
        print_lst.append('\nCollection: %s\n' % collection)
        df_print = tracker.loc[tracker['collection'] == collection].drop('collection', axis=1)
        print_lst.append(tabulate(df_print, showindex=False, headers=df_print.columns))

    print_str = '\n'.join(print_lst).strip()
    if outfile is None:
        print(print_str)
    else:
        with open(outfile, 'w') as f:
            f.write(print_str)

    if verbose:
        pydoni.vb.program_complete()

    result['n_collections'] = len(tracker['collection'].unique())
    pydoni.pydonicli_register({k: v for k, v in locals().items() if k in ['args', 'result']})
