import time
import re
import click
from emoji import emojize
from tqdm import trange
from os.path import expanduser
from datetime import datetime


def echo(
        msg,
        indent       = 0,
        sleep        = 0,
        timestamp    = False,
        success      = False,
        warn         = False,
        error        = False,
        error_msg    = None,
        abort        = False,
        fn_name      = None,
        fg           = None,
        bg           = None,
        bold         = None,
        dim          = None,
        underline    = None,
        blink        = None,
        reverse      = None,
        return_str   = False,
        notify       = False,
        notification = dict(
            title         = '',
            subtitle      = None,
            message       = None,
            app_icon      = None,
            content_image = None,
            command       = None,
            open_iterm    = False
            )
        ):
    """
    Update stdout with custom message and many custom parameters including indentation,
    timestamp, warning/error message, text styles, and more!

    Arguments:
        msg {str} -- message to print to console
    
    Keyword Arguments:
        indent       {int}  -- indentation level of message printed to console
        sleep        {int}  -- number of seconds to pause program after printing message
        timestamp    {bool} -- if True, print datetimestamp preceding message
        success      {bool} -- if True, print 'Success: ' in green preceding message
        warn         {bool} -- if True, print 'Warning: ' in yellow preceding message
        error        {bool} -- if True, print 'Error: ' in red preceding message
        error_msg    {str}  -- python error message. Intended for use in try/except. Pass in `str(e)` here.
        abort        {bool} -- if True, raise Exception with `msg` as error message.
        fn_name      {str}  -- name of function, if any, that echo() was called from. Will include function in printed message. Useful for debugging. Only applied if one or more of `warn`, `error` or `abort` are set to True
        fg           {str}  -- color string indicator color of text. One of [None, 'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'],
        bg           {str}  -- color string indicator color of background of text. One of [None, 'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'],
        bold         {bool} -- if True, print message with bold effect
        dim          {bool} -- if True, print message with dim effect
        underline    {bool} -- if True, print message with underline effect
        blink        {bool} -- if True, print message with blink effect
        reverse      {bool} -- if True, print message with reverse effect (foreground/background reversed).
        return_str   {bool} -- if True, return string instead of printing (default: {False})
        notify       {bool} -- if True, invoke `pydoni.os.macos_notify()`. Notification customizations can be altered in `notification` parameter.
        notification {dict} -- customize macOS notification. Requires that `notify` set to True
            title         {str}  -- title of notification
            subtitle      {str}  -- subtitle of notification
            app_icon      {str}  -- path to app icon image to display on left side of notification
            content_image {str}  -- path to content image to display within notification
            command       {str}  -- bASH string to execute on notification click
            open_iterm    {bool} -- if True, sets `command` to "open /Applications/iTerm.app" to open iTerm application on notification click.
    
    Returns:
        nothing
    """

    # Save original message before any editing is done if the message will be used in a 
    # macOS notification
    if notify:
        msg_raw = msg

    # Apply 'click' styles to text string
    msg = click.style(msg, fg=fg, bg=bg, bold=bold, dim=dim, underline=underline,
        blink=blink, reverse=reverse)

    # Add preceding colored string for specified keyword args
    if error:
        ew_string = click.style('Error: ', fg='red')
    elif warn:
        ew_string = click.style('Warning: ', fg='yellow')
    elif success:
        ew_string = click.style('Success: ', fg='green')
    else:
        ew_string = ''

    # Function name string
    if fn_name:
        fnn_string = click.style('<fn: ', fg='white') + \
            click.style(fn_name.replace('(', '').replace(')', '') + '()', fg='white', underline=True) + \
            click.style('> ', fg='white')
    else:
        fnn_string = ''

    # Add indentation. If not specified, adds an empty string
    idt_string = '  ' * indent if indent > 0 else ''

    # Add timestamp if specified
    ts_string = click.style(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' ', fg='cyan') if timestamp else ''
    
    # Construct message
    msg_out = ts_string + fnn_string + idt_string + ew_string + msg

    # Print message to STDOUT
    if not abort and not return_str:
        click.echo(msg_out)
    
    # If `error_msg` is specified, print after `msg`
    if error_msg and not abort:
        print(error_msg)

    # Throw macOS notification if specified
    if notify:
        # Assign default values if only partial notification elements supplied
        # Ex. If a user supplies notification=dict(title='test title'), then all other
        # notification elements (subtitle, app_icon, ...) will be not present in dictionary.
        # Assign these nonexistent values to default.
        notif_default = {
            'title': '',
            'subtitle': None,
            'message': None,
            'app_icon': None,
            'content_image': None,
            'command': None,
            'open_iterm': False
        }
        for k, v in notif_default.items():
            if k not in notification.keys():
                if k in ['app_icon', 'content_image']:
                    if isinstance(v, str):
                        if '~' in v:
                            v = expanduser(v)
                notification[k] = v

        notification['message'] = msg_raw if notification['message'] is None else notification['message']

        pydoni.os.macos_notify(
            title         = notification['title'],
            subtitle      = notification['subtitle'],
            message       = notification['message'],
            app_icon      = notification['app_icon'],
            content_image = notification['content_image'],
            command       = notification['command'],
            open_iterm    = notification['open_iterm']
        )
    
    # Pause script execution if specified
    if sleep > 0:
        time.sleep(sleep)
    
    # Exit program if specified
    if abort:
        raise Exception(msg)

    if return_str:
        return msg_out


def clickfmt(string, fmt):
    """
    Create frequently-used `click` formating styles.
    
    Arguments:
        string {str} -- text string
        fmt {str} -- format type, one of ['numeric', 'filename', 'filepath', 'url', 'date', 'arrow', 'green', 'red', 'yellow', 'cyan']
    
    Returns:
        {str}
    """
    if fmt == 'numeric':
        return click.style(string, fg='yellow', bold=True)
    elif fmt == 'filename':
        return click.style(string, fg='magenta', bold=True)
    elif fmt == 'filepath' or fmt == 'url':
        return click.style(string, fg='cyan', bold=True)
    elif fmt == 'date':
        return click.style(string, fg='blue', bold=True)
    elif fmt == 'arrow':
        return click.style(string, fg='white', bold=True)
    elif fmt == 'green':
        return click.style(string, fg='green', bold=True)
    elif fmt == 'red':
        return click.style(string, fg='red', bold=True)
    elif fmt == 'yellow':
        return click.style(string, fg='yellow', bold=True)
    elif fmt == 'white':
        return click.style(string, fg='white', bold=True)
    elif fmt == 'cyan':
        return click.style(string, fg='cyan', bold=True)
    elif fmt == 'blue':
        return click.style(string, fg='blue', bold=True)
    else:
        echo("Invalid 'fmt' parameter", error=True, abort=False)


def verbose_header(string, time_in_sec=None, round_digits=2):
    """
    Print STDOUT verbose section header and optionally print estimated time.
    
    Arguments:
        string {str} -- header text

    Keyword Arguments:
        time_in_sec  {int} -- time in seconds that code section will take (default: None)
        round_digits {int} -- round estimated time to this many digits (default: 2)
    
    Returns:
        nothing
    """

    # Format string as title
    title = click.style(string, fg='white', bold=True)

    # If time in seconds is given, augment title to incorporate estimated time
    if isinstance(time_in_sec, int) or isinstance(time_in_sec, float):
        # Get estimated time as dictionary
        esttime = pydoni.pyobj.fmt_seconds(time_in_sec=time_in_sec, units='auto', round_digits=round_digits)
        title = '{} {} Est. time {}'.format(
            title,
            click.style('->', fg='white', bold=True),
            click.style(str(esttime['value']) + ' ' + esttime['units'], fg='yellow', bold=True))
    
    # Print message
    echo(title)


def print_columns(lst, ncol=2, delay=None):
    """
    Print a list as side-by-side columns.
    
    Arguments:
        lst   {list} -- list to print to screen

    Keyword Arguments:
        ncol  {int} -- number of columns to print to screen (default: 2)
        delay {int} or {float} -- if specified, delay this many seconds after each line is printed (default: None)
    
    Returns:
        nothing
    """
    
    def chunks(lst, chunk_size):
        """
        Split a list into a list of lists.
        
        Arguments:
            lst {list} -- list to split
            chunk_size {int} -- size of chunks
        
        Returns:
            {list}
        """
        for i in range(0, len(lst), chunk_size):
            yield lst[i:i + chunk_size]

    lstlst = list(chunks(lst, ncol))
    col_width = max(len(word) for row in lstlst for word in row) + 2
    for row in lstlst:
        print(''.join(word.ljust(col_width) for word in row))
        if delay is not None:
            if delay > 0:
                time.sleep(delay)


def program_complete(
        msg          = 'Program complete!',
        emoji_string = ':rocket:',
        start_time   = None,
        end_time     = None,
        notify       = False,
        notification = dict(
            title         = '',
            subtitle      = None,
            message       = None,
            app_icon      = None,
            content_image = None,
            command       = None,
            open_iterm    = False
        ),
        use_stdout = False
    ):
    """
    Print to STDOUT indicating program was completed. Optionally include the elapsed program
    time. Optionally send a macOS notification or a notification email indicating program
    completion.
    
    Keyword Arguments:
        msg {str} -- custom message to print instead of default (default: {'Program complete!'})
        emoji_string {str} -- name of emoji to print if any (default: {':thumbs_up:'})
        start_time {float} -- start time of program, output of time.time() (default: {None})
        end_time {float} -- end time of program, output of time.time() (default: {None})
        notify {bool} -- if True, notify user with pydoni.os.macos_notify() (default: {False})
        notification {dict} -- customize macOS notification. Requires that `notify` set to True
            title         {str}  -- title of notification
            subtitle      {str}  -- subtitle of notification
            app_icon      {str}  -- path to app icon image to display on left side of notification
            content_image {str}  -- path to content image to display within notification
            command       {str}  -- BASH string to execute on notification click
            open_iterm    {bool} -- if True, sets `command` to "open /Applications/iTerm.app" to open iTerm application on notification click.
        use_stdout {bool} -- print to STDOUT instead of using logger (False)

    Returns:
        nothing
    """

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)

    # Save original message before any editing is done if the message will be used in a
    # macOS notification
    if notify:
        msg_raw = msg

    # Add colons surrounding emoji string if not already present
    emoji_string = ':' + emoji_string.replace(':', '') + ':'

    # Add emoji if specified
    if emoji_string is not None:
        msg = '{} {}'.format(click.style(msg, fg='green'), emojize(emoji_string, use_aliases=True))
    else:
        msg = click.style(msg, fg='green')

    # Get elapsed time if specified
    if start_time is not None and end_time is not None:
        assert isinstance(start_time, float)
        assert isinstance(end_time, float)
        diff = pydoni.pyobj.fmt_seconds(end_time - start_time, units='auto', round_digits=2)
        msg = msg + ' Elapsed time: {}'.format(
            click.style('{} {}'.format(
                diff['value'],
                diff['units']),
                fg='yellow', bold=True))

        # Add to msg_raw to include in notification
        if notify:
            msg_raw = msg_raw + ' Elapsed time: {} {}'.format(diff['value'], diff['units'])

    # Print message and notify if specified
    if notify:
        notification['message'] = msg_raw
        pydoni.os.macos_notify(**notification)
    
    if use_stdout:
        echo(msg)

    logger.info(msg)


def stabilize_postfix(key, max_len=20, fillchar='•', side='right'):
    """
    Create "stabilized" postfix (of consistent length) to be fed into
    a tqdm progress bar. This ensures that the postfix is always of
    a certain length, which causes the tqdm progress bar to be stable
    rather than moving left to right when keys of length smaller
    than `max_len` are encountered.

    Arguments:
        key {str} -- string to set as postfix

    Keyword Arguments:
        max_len {int} -- length of postfix (default: {20})
        fillchar {str} -- character to fill any spaces on the left with (default: {'•'})
        side {str} -- which side of postfix substring to keep, one of ['left', 'right'] (default: {'right'})

    Returns:
        {str}
    """
    assert side in ['left', 'right']

    if side == 'left':
        postfix = key[0:max_len].ljust(max_len, fillchar)
    elif side == 'right':
        postfix = key[-max_len:].rjust(max_len, fillchar)

    m = re.match(r'^ +', postfix)
    if m:
        leading_spaces = m.group(0)
        postfix = re.sub(r'^ +', fillchar * len(leading_spaces), postfix)

    m = re.match(r' +$', postfix)
    if m:
        trailing_spaces = m.group(0)
        postfix = re.sub(r'^ +', fillchar * len(trailing_spaces), postfix)

    return postfix


def line_messages(messages):
    """
    Print messages below TQDM progress bar.

    Arguments:
        messages {list} -- list of messages to print, each on its own line

    Returns:
        nothing
    """
    for i, m in enumerate(messages, 1):
        trange(1, desc=str(m), position=i, bar_format='{desc}')


import pydoni
import pydoni.os
