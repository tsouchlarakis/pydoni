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
        msg          (str) : Mandatory. Message to print to console.
        indent       (int) : Optional. Indentation level of message printed to console.
        sleep        (int) : Optional. Number of seconds to pause program after printing message.
        timestamp    (bool): Optional. If True, print datetimestamp preceding message.
        warn         (bool): Optional. If True, print 'WARNING: ' in yellow preceding message.
        error        (bool): Optional. If True, print 'ERROR: ' in red preceding message.
        error_msg    (str) : Optional. Python error message. Intended for use in try/except. Pass in `str(e)` here.
        abort        (bool): Optional. If True, print 'ERROR (fatal): ' in red preceding message AND exit program.
        fn_name      (str) : Optional. Name of function, if any, that echo() was called from. Will include function in printed message. Useful for debugging. Only applied if one or more of `warn`, `error` or `abort` are set to True
        fg           (str) : Optional. Color string indicator color of text. One of [None, 'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'],
        bg           (str) : Optional. Color string indicator color of background of text. One of [None, 'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'],
        bold         (bool): Optional. If True, print message with bold effect.
        dim          (bool): Optional. If True, print message with dim effect.
        underline    (bool): Optional. If True, print message with underline effect.
        blink        (bool): Optional. If True, print message with blink effect.
        reverse      (bool): Optional. If True, print message with reverse effect (foreground/background reversed).
        notify       (bool): Optional. If True, invoke `macos_notify()`. Notification customizations can be altered in `notification` parameter.
        notification (dict): Optional. Customize macOS notification. Requires that `notify` set to True.
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
            notification['message'] = None
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
            message       = msg_raw,
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

def clickfmt(string, fmt=['numeric', 'filename', 'filepath', 'url', 'date', 'arrow', 'green', 'red', 'yellow', 'cyan']):
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

def verboseHeader(string, time_in_sec, round_digits=2):
    import click
    from pydoni.vb import echo
    from pydoni.pyobj import fmtSeconds
    esttime = fmtSeconds(time_in_sec, round_digits=round_digits)
    echo('{} {} Est. time: {}'.format(
        click.style(string, fg='white', bold=True),
        click.style('->', fg='white', bold=True),
        click.style(str(esttime['value']) + ' ' + esttime['units'], fg='yellow', bold=True)))

def printColumns(lst, ncol, delay=None):  # Print a list as side-by-side columns
    import time
    def chunks(lst, chunk_size):
        for i in range(0, len(lst), chunk_size):
            yield lst[i:i + chunk_size]
    lstlst = list(chunks(lst, ncol))
    col_width = max(len(word) for row in lstlst for word in row) + 2
    for row in lstlst:
        print(''.join(word.ljust(col_width) for word in row))
        if delay:
            if delay > 0:
                time.sleep(delay)

def programComplete(custom_string=None):
    import emoji, click
    msg = 'Program complete!' if not custom_string else custom_string
    click.echo('{} {}'.format(click.style(msg, fg='green'), emoji.emojize(':thumbs_up:')))
