def echo(msg, indent=0, sleep=0, timestamp=False, 
    warn=False, error=False, error_msg=None, abort=False, fn_name=None,
    fg=None, bg=None, bold=None, dim=None, underline=None, blink=None, reverse=None):
    """Update stdout with custom message and optional indent, current datetime and text styles
    Colors: [None, 'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white']"""
    import click
    msg = click.style(msg, fg=fg, bg=bg, bold=bold, dim=dim, underline=underline,
        blink=blink, reverse=reverse)
    if error or abort or warn:
        msg = '{}{}{} {}'.format(
            click.style('ERROR' if error or abort else 'WARNING',
                       fg='red' if error or abort else 'yellow', bold=True),
            click.style(' (fatal)' if abort else '', fg='red', bold=True),
            click.style(' in function {}():'.format(fn_name) if fn_name else ':',
                fg='red' if error or abort else 'yellow', bold=True), msg)
    tab = '  ' * indent if indent > 0 else ''
    msg = tab + msg
    if timestamp:
        from datetime import datetime
        timestamp = click.style(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), fg='cyan', bold=True)
        if tab == '':
            msg = timestamp + ' ' + msg
        else:
            msg = timestamp + msg
    click.echo(msg)
    if error_msg:
        print(error_msg)
    if sleep > 0:
        import time
        time.sleep(sleep)
    if abort:
        import sys
        sys.exit()

def echoError(msg, error_msg=None, fn_name=None, abort=True, stop=None):
    import sys, click
    if fn_name:
        print_msg = '{} {} {}'.format(
            click.style('ERROR in function', fg='red', bold=True),
            click.style(fn_name + '():', fg='red', bold=True), msg)
    else:
        print_msg = '{} {}'.format(click.style('ERROR:', fg='red', bold=True), msg)
    click.echo(print_msg)
    if error_msg:
        click.echo(error_msg)
    if abort or stop:
        quit_msg = 'Quitting program'
        click.secho(quit_msg, fg='red', bold=True)
        exit()

def echoWarn(msg, fn_name=None):
    import sys, click
    if fn_name:
        print_msg = '{} {} {}'.format(
            click.style('WARNING in function', fg='yellow', bold=True),
            click.style(fn_name + '():', fg='yellow', bold=True), msg)
    else:
        print_msg = '{} {}'.format(click.style('WARNING:', fg='yellow', bold=True), msg)
    click.echo(print_msg)

def clickfmt(string, fmt=['numeric', 'filename', 'filepath', 'url', 'date', 'arrow', 'green', 'red', 'yellow']):
    import click
    from PyFunctions import echoError
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
    else:
        echoError("Invalid 'fmt' parameter", abort=False)

def verboseHeader(string, time_in_sec, round_digits=2):
    import click
    from PyFunctions import echo, fmtSeconds
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
        if delay > 0:
            time.sleep(delay)