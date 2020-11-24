import pydoni
import pydoni.opsys


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
        arrow        = None,
        notification = dict(
            title         = '',
            subtitle      = None,
            message       = None,
            app_icon      = None,
            content_image = None,
            command       = None,
            open_iterm    = False)):
    """
    Update stdout with custom message and many custom parameters including indentation,
    timestamp, warning/error message, text styles, and more!

    :param msg: message to print to console
    :type msg: str

    :param indent: indentation level of message printed to console
    :type indent: int
    :param sleep: number of seconds to pause program after printing message
    :type sleep: int
    :param timestamp: print datetimestamp preceding message
    :type timestamp: bool
    :param success: print 'Success: ' in green preceding message
    :type success: bool
    :param warn: print 'Warning: ' in yellow preceding message
    :type warn: bool
    :param error: print 'Error: ' in red preceding message
    :type error: bool
    :param error_msg: python error message. Intended for use in try/except.
                      Pass in `str(e)` here.
    :type error_msg: str
    :param abort: raise Exception with `msg` as error message.
    :type abort: bool
    :param fn_name: name of function, if any, that echo() was called from. Will
                    include function in printed message. Useful for debugging. Only
                    applied if one or more of `warn`, `error` or `abort` are set to True
    :type fn_name: str
    :param fg: color string indicator color of text. One of [None, 'black', 'red',
               'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'],
    :type fg: str
    :param bg: color string indicator color of background of text. One of [None,
               'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'],
    :type bg: str
    :param bold: print message with bold effect
    :type bold: bool
    :param dim: print message with dim effect
    :type dim: bool
    :param underline: print message with underline effect
    :type underline: bool
    :param blink: print message with blink effect
    :type blink: bool
    :param reverse: print message with reverse effect (foreground/background reversed).
    :type reverse: bool
    :param return_str: return string instead of printing
    :type return_str: bool
    :param notify: invoke `pydoni.opsys.macos_notify()`. Notification customizations can
                   be altered in `notification` parameter.
    :type notify: bool
    :param arrow: color of arrow to display before message
    :type arrow: str
    :param notification: customize macOS notification. Requires that `notify` set to True
    :type notification: dict
        title: title of notification
        subtitle: subtitle of notification
        app_icon: path to app icon image to display on left side of notification
        content_image: path to content image to display within notification
        command: BASH string to execute on notification click
        open_iterm: sets `command` to "open /Applications/iTerm.app" to open
                    iTerm application on notification click.
    """
    import click
    import time
    import os
    from datetime import datetime

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

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

    arrow_string = click.style('==>', fg=arrow) if arrow is not None else ''

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
    msg_out = ts_string + fnn_string + idt_string + arrow_string + ew_string + msg

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
                            v = os.path.expanduser(v)
                notification[k] = v

        notification['message'] = msg_raw if notification['message'] is None else notification['message']

        pydoni.opsys.macos_notify(
            title         = notification['title'],
            subtitle      = notification['subtitle'],
            message       = notification['message'],
            app_icon      = notification['app_icon'],
            content_image = notification['content_image'],
            command       = notification['command'],
            open_iterm    = notification['open_iterm'])

    # Pause script execution if specified
    if sleep > 0:
        time.sleep(sleep)

    # Exit program if specified
    if abort:
        raise Exception(msg)

    if return_str:
        return msg_out


def verbose_header(string, time_in_sec=None, round_digits=2):
    """
    Print STDOUT verbose section header and optionally print estimated time.

    :param string: header text
    :type string: str
    :param time_in_sec: time in seconds that code section will take
    :type time_in_sec: int
    :param round_digits: round estimated time to this many digits
    :type round_digits: int
    """
    import click

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    title = click.style(string, fg='white', bold=True)

    # If time in seconds is given, augment title to incorporate estimated time
    if isinstance(time_in_sec, int) or isinstance(time_in_sec, float):
        # Get estimated time as dictionary
        esttime = pydoni.fmt_seconds(time_in_sec=time_in_sec, units='auto', round_digits=round_digits)
        title = '{} {} Est. time {}'.format(
            title,
            click.style('->', fg='white', bold=True),
            click.style(str(esttime['value']) + ' ' + esttime['units'], fg='yellow', bold=True))

    pydoni.vb.echo(title)


def print_columns(lst, ncol=2, delay=None):
    """
    Print a list as side-by-side columns.

    :param lst: list to print to screen
    :type lst: list
    :param ncol: number of columns to print to screen
    :type ncol: int
    :param delay: delay this many seconds after each line is printed
    :type delay: int or float
    """
    import time

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    def chunks(lst, chunk_size):
        """
        Split a list into a list of lists.

        :param lst: list to split
        :type lst: list
        :param chunk_size: size of chunks
        :type chunk_size: int
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
        use_stdout = False):
    """
    Print to STDOUT indicating program was completed. Optionally include the elapsed program
    time. Optionally send a macOS notification or a notification email indicating program
    completion.

    :param msg: custom message to print instead of default
    :type msg: str
    :param emoji_string: name of emoji to print if any
    :type emoji_string: str
    :param start_time: start time of program, output of time.time()
    :type start_time: float
    :param end_time: end time of program, output of time.time()
    :type end_time: float
    :param notify: notify user with pydoni.opsys.macos_notify()
    :type notify: bool
    :param notification: customize macOS notification. Requires that `notify` set to True
    :type notification: dict
        title: title of notification
        subtitle: subtitle of notification
        app_icon: path to app icon image to display on left side of notification
        content_image: path to content image to display within notification
        command: BASH string to execute on notification click
        open_iterm: sets `command` to "open /Applications/iTerm.app" to open iTerm application on notification click.
    :param use_stdout: print to STDOUT instead of using logger (False)
    :type use_stdout: bool
    """
    import click
    from emoji import emojize

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

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
        diff = pydoni.fmt_seconds(end_time - start_time, units='auto', round_digits=2)
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
        pydoni.opsys.macos_notify(**notification)

    if use_stdout:
        pydoni.vb.echo(msg)

    pydoni.vb.echo(msg)


def stabilize_postfix(key, max_len=20, fillchar='•', side='right'):
    """
    Create "stabilized" postfix (of consistent length) to be fed into
    a tqdm progress bar. This ensures that the postfix is always of
    a certain length, which causes the tqdm progress bar to be stable
    rather than moving left to right when keys of length smaller
    than `max_len` are encountered.

        :param key: string to set as postfix
        :type key: str

        :param max_len: length of postfix
        :type max_len: int
        :param fillchar: character to fill any spaces on the left with
        :type fillchar: str
        :param side: which side of postfix substring to keep, one of ['left', 'right']
        :type side: str
    """
    import re
    assert side in ['left', 'right']

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

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

        :param messages: list of messages to print, each on its own line
        :type messages: list
    """
    from tqdm import trange

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    for i, m in enumerate(messages, 1):
        trange(1, desc=str(m), position=i, bar_format='{desc}')
