def echo(
    msg,
    indent=0,
    sleep=0,
    timestamp=False,
    warn=False,
    error=False,
    error_msg=None,
    abort=False,
    fn_name=None,
    fg=None,
    bg=None,
    bold=None,
    dim=None,
    underline=None,
    blink=None,
    reverse=None,
    notify=False,
    notification=dict(
        title='',
        subtitle=None,
        message=None,
        app_icon=None,
        content_image=None,
        command=None,
        open_iterm=False
        )
    ):
    """
    Update stdout with custom message and many custom parameters including indentation, timestamp,
    warning/error message, text styles, and more.

    Args
        msg          (str) : [mandatory] Message to print to console.
        indent       (int) : [optional] Indentation level of message printed to console.
        sleep        (int) : [optional] Number of seconds to pause program after printing message.
        timestamp    (bool): [optional] If True, print datetimestamp preceding message.
        warn         (bool): [optional] If True, print 'WARNING: ' in yellow preceding message.
        error        (bool): [optional] If True, print 'ERROR: ' in red preceding message.
        error_msg    (str) : [optional] Python error message. Intended for use in try/except. Pass in `str(e)` here.
        abort        (bool): [optional] If True, print 'ERROR (fatal): ' in red preceding message AND exit program.
        fn_name      (str) : [optional] Name of function, if any, that echo() was called from. Will include function in printed message. Useful for debugging. Only applied if one or more of `warn`, `error` or `abort` are set to True
        fg           (str) : [optional] Color string indicator color of text. One of [None, 'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'],
        bg           (str) : [optional] Color string indicator color of background of text. One of [None, 'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'],
        bold         (bool): [optional] If True, print message with bold effect.
        dim          (bool): [optional] If True, print message with dim effect.
        underline    (bool): [optional] If True, print message with underline effect.
        blink        (bool): [optional] If True, print message with blink effect.
        reverse      (bool): [optional] If True, print message with reverse effect (foreground/background reversed).
        notify       (bool): [optional] If True, invoke `macos_notify()`. Notification customizations can be altered in `notification` parameter.
        notification (dict): [optional] Customize macOS notification. Requires that `notify` set to True.
            title         (str) : Title of notification.
            subtitle      (str) : Subtitle of notification.
            app_icon      (str) : Path to app icon image to display on left side of notification.
            content_image (str) : Path to content image to display within notification.
            command       (str) : BASH string to execute on notification click.
            open_iterm    (bool): If True, sets `command` to "open /Applications/iTerm.app" to open iTerm application on notification click.
    
    Returns
        Nothing
    """
    import os, click

    # Save original message before any editing is done if the message will be used in a 
    # macOS notification
    if notify:
        msg_raw = msg

    # Apply 'click' styles to text string
    msg = click.style(msg, fg=fg, bg=bg, bold=bold, dim=dim, underline=underline,
        blink=blink, reverse=reverse)

    # Add 'ERROR: ' or 'ERROR (fatal): ' or 'WARNING: ' to beginning of string, and add function
    # name if specified
    if error or abort or warn:
        msg = '{}{}{} {}'.format(
            click.style('ERROR' if error or abort else 'WARNING',
                       fg='red' if error or abort else 'yellow', bold=True),
            click.style(' (fatal)' if abort else '', fg='red', bold=True),
            click.style(' in function {}():'.format(fn_name) if fn_name else ':',
                fg='red' if error or abort else 'yellow', bold=True), msg)
    
    # Add indentation. If not specified, adds an empty string
    tab = '  ' * indent if indent > 0 else ''
    msg = tab + msg

    # Add timestamp if specified
    if timestamp:
        from datetime import datetime
        timestamp = click.style(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), fg='cyan', bold=False)
        if tab == '':
            msg = timestamp + ' ' + msg
        else:
            msg = timestamp + msg
    
    # Print message to STDOUT
    click.echo(msg)
    
    # If `error_msg` is specified, print after `msg`
    if error_msg:
        print(error_msg)

    # Throw macOS notification if specified
    if notify:
        from pydoni.os import macos_notify
        # Assign default values if only partial notification elements supplied
        # Ex. If a user supplies notification=dict(title='test title'), then all other
        # notification elements (subtitle, app_icon, ...) will be not present in dictionary.
        # Assign these nonexistent values to default.
        if 'title' not in notification.keys():
            notification['title'] = ''
        if 'subtitle' not in notification.keys():
            notification['subtitle'] = None
        if 'message' not in notification.keys():
            notification['message'] = msg_raw
        if 'app_icon' not in notification.keys():
            notification['app_icon'] = None
        if isinstance(notification['app_icon'], str):
            if '~' in notification['app_icon']:
                notification['app_icon'] = os.path.expanduser(notification['app_icon'])
        if 'content_image' not in notification.keys():
            notification['content_image'] = None
        if isinstance(notification['content_image'], str):
            if '~' in notification['content_image']:
                notification['content_image'] = os.path.expanduser(notification['content_image'])
        if 'command' not in notification.keys():
            notification['command'] = None
        if 'open_iterm' not in notification.keys():
            notification['open_iterm'] = False
        macos_notify(
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
        import time
        time.sleep(sleep)
    
    # Exit program if specified
    if abort:
        quit()


def clickfmt(string, fmt):
    """
    Create frequently-used `click` formating styles.
    Args
        string (str): text string
        fmt    (str): format type, one of ['numeric', 'filename', 'filepath', 'url', 'date', 'arrow', 'green', 'red', 'yellow', 'cyan']
    Returns
        str
    """
    import click
    from pydoni.vb import echo
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
    Args
        string       (str): header text
        time_in_sec  (int): [optional] time in seconds that code section will take
        round_digits (int): [optional] round estimated time to this many digits
    Returns
        nothing
    """
    import click
    from pydoni.vb import echo
    from pydoni.pyobj import fmt_seconds

    # Format string as title
    title = click.style(string, fg='white', bold=True)

    # If time in seconds is given, augment title to incorporate estimated time
    if isinstance(time_in_sec, int):
        # Get estimated time as dictionary
        esttime = fmt_seconds(time_in_sec=time_in_sec, units='auto', round_digits=round_digits)
        title = '{} {} Est. time {}'.format(
            title,
            click.style('->', fg='white', bold=True),
            click.style(str(esttime['value']) + ' ' + esttime['units'], fg='yellow', bold=True))
    
    # Print message
    echo(title)


def print_columns(lst, ncol=2, delay=None):
    """
    Print a list as side-by-side columns.
    Args
        lst   (list)        : list to print to screen
        ncol  (int)         : number of columns to print to screen
        delay (int or float): [optional] if specified, delay this many seconds after each line is printed
    Returns
        nothing
    """
    import time
    
    def chunks(lst, chunk_size):
        """
        Split a list into a list of lists.
        Args
            lst        (list): list to split
            chunk_size (int) : size of chunks
        Returns
            list
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
    msg='Program complete!',
    emoji_string=':thumbs_up:',
    start_time=None,
    end_time=None,
    notify=False,
    notification=dict(
        title='',
        subtitle=None,
        message=None,
        app_icon=None,
        content_image=None,
        command=None,
        open_iterm=False
    )
    ):
    """
    Print to STDOUT indicating program was completed. Optionally include the elapsed program
    time. Optionally send a macOS notification or a notification email indicating program
    completion.
    
    Args
        emoji_string (str)  : Name of emoji to display. Defaults to ':thumbs_up:'. Set to None if no emoji should be printed.
        start_time   (float): Start time of program as output of time.time(). Used to calculate elapsed time. Leave blank if elapsed time should not be printed.
        end_time     (float): End time of program as output of time.time(). Used to calculate elapsed time. Leave blank if elapsed time should not be printed.
        notify       (bool) : If True, execute `macos_notify()` to create a macOS notification.
    Returns
        nothing
    """
    import emoji, click
    from pydoni.vb import echo
    from pydoni.pyobj import fmt_seconds

    # Save original message before any editing is done if the message will be used in a
    # macOS notification
    if notify:
        msg_raw = msg

    # Add colons surrounding emoji string if not already present
    emoji_string = ':' + emoji_string.replace(':', '') + ':'

    # Add emoji if specified
    if emoji_string is not None:
        msg = '{} {}'.format(click.style(msg, fg='green'), emoji.emojize(emoji_string))
    else:
        msg = click.style(msg, fg='green')

    # Get elapsed time if specified
    if start_time is not None and end_time is not None:
        import time
        assert isinstance(start_time, float)
        assert isinstance(end_time, float)
        diff = fmt_seconds(end_time - start_time, units='auto', round_digits=2)
        msg = msg + ' Elapsed time: {}'.format(
            click.style('{} {}'.format(
                diff['value'],
                diff['units']),
                fg='yellow', bold=True)
        )

        # Add to msg_raw to include in notification
        msg_raw = msg_raw + ' Elapsed time: {} {}'.format(diff['value'], diff['units'])

    # Print message and notify if specified
    if notify:
        notification['message'] = msg_raw
        echo(msg, notify=True, notification=notification)
    else:
        echo(msg)
