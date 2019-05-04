def dictSApply(func, d):  # Apply function to each terminal element of a dictionary
    if (isinstance(d, str)):
        return func(d)
    elif (isinstance(d, dict)):
        return { key : dictSApply(func, d[key]) for key in d }
    elif (isinstance(d, list)):
        return [ dictSApply(func, val) for val in d ]

class DoniDict(dict):  # Dictionary class with recursive 'get' method
    def __init__(self, mydict):
        import os
        self.mydict = dictSApply(os.path.expanduser, mydict)
    def rget(self, *args, **kwargs):
        default = kwargs.get('default')
        cursor = self.mydict
        for a in args:
            if cursor is default: break
            cursor = cursor.get(a, default)
        return cursor

def systime(stripchars=False):
    # Print the current time formatted as a string
    import datetime
    if stripchars:
        now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    else:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return now

def sysdate(stripchars=False):
    # Print the current date formatted as a string
    import datetime
    if stripchars:
        now = datetime.datetime.now().strftime("%Y%m%d")
    else:
        now = datetime.datetime.now().strftime("%Y-%m-%d")
    return now

def assert_len(varlist, varnames):  # Ensure lengths of variables are equal, otherwise error
    import click
    from pydoni.vb import echo
    lengths = [len(x) for x in varlist]
    if len(set(lengths)) > 1:
        echo("Unequal variable lengths: {}. Respective lengths are {}".format(
            ', '.join("'" + click.style(item,      fg='red', bold=True) + "'" for item in varnames),
            ', '.join("'" + click.style(str(item), fg='red', bold=True) + "'" for item in lengths)),
        fn_name='assert_len', abort=True)

def userSelectFromList(lst, indent=0, msg=None, allow_range=True):
    import re
    from pydoni.vb import echo
    tab = '\t' * indent
    if not msg:
        msg = 'Please make a selection (hyphen-separated range ok): ' \
            if allow_range else 'Please make a single selection: '
    for i, item in enumerate(lst):
        print('{}({}) {}'.format(tab, str(i+1), item))
    invalid = True
    while invalid:
        uin = input(msg + ': ' if not msg.rstrip().endswith(':') else msg)
        if re.search(r'^(\d+-\d+)$', uin):
            if allow_range:
                uin = uin.split('-')
                uin = list(range(int(uin[0]), int(uin[1])+1))
                if uin[len(uin)-1] > len(lst) or uin[0] < 1:
                    echo('Entry must be between {} and {}'.format('1', str(len(lst))), error=True)
                    invalid = True
                    continue
                else:
                    val = [lst[i-1] for i in uin]
                    break
            else:
                echo("Range entered but parameter 'allow_range' is False", error=True, abort=False)
                invalid = True
                continue
        elif re.search(r'^(\d+)$', uin):
            uin = int(uin)
            if uin < 1 or uin > len(lst):
                echo('Entry must be between {} and {}'.format('1', str(len(lst))), error=True)
                invalid = True
                continue
            return lst[uin-1]
        else:
            echo("Invalid entry. Must match either '\d+' or '\d+-\d+'", error=True)
            invalid = True
            continue
    return val

def fmt_seconds(time_in_sec, units='auto', round_digits=4):
    """Format time in seconds to a custom string"""
    if units == 'auto':
        if time_in_sec < 60:
            time_diff = round(time_in_sec, round_digits)
            time_measure = 'seconds'
        elif time_in_sec >= 60 and time_in_sec < 3600:
            time_diff = round(time_in_sec/60, round_digits)
            time_measure = 'minutes'
        elif time_in_sec >= 3600 and time_in_sec < 86400:
            time_diff = round(time_in_sec/3600, round_digits)
            time_measure = 'hours'
        else:
            time_diff = round(time_in_sec/86400, round_digits)
            time_measure = 'days'
    elif units in ['seconds', 'minutes', 'hours', 'days']:
        time_measure = units
        if units == 'seconds':
            time_diff = round(time_in_sec, round_digits)
        elif units == 'minutes':
            time_diff = round(time_in_sec/60, round_digits)
        elif units == 'minutes':
            time_diff = round(time_in_sec/3600, round_digits)
        else:  # Days
            time_diff = round(time_in_sec/86400, round_digits)
    else:
        print("Invalid 'units' parameter. Must be one of 'auto', 'seconds', 'minutes', 'hours' or 'days'")
        return None
    return dict(zip(['units', 'value'], [time_measure, time_diff]))

def listmode(lst):  # Get the most frequently-occurring value in a list
    return max(set(lst), key=lst.count)

def dict_filter(d, keys):
    return {k.lower().replace(' ', '_'): v for k, v in d.items() if k.lower().replace(' ', '_') in keys}

def capNthChar(string, n):
    """Capitalize the Nth character of a string. If 'n' is out of range, return original string"""
    if n >= len(string):
        return string
    return string[:n] + string[n].capitalize() + string[n+1:]

def replaceNthChar(string, n, replacement):
    if n >= len(string):
        return string
    return string[:n] + replacement + string[n+1:]

def insertNthChar(string, n, char):
    if n >= len(string):
        return string
    return string [:n] + char + string[n:]

def human_filesize(nbytes: int) -> str:
    """Convert number of bytes to human-readable filesize string"""
    # https://stackoverflow.com/questions/5194057/better-way-to-convert-file-sizes-in-python
    base = 1
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']:
        n = nbytes / base
        if n < 9.95 and unit != 'B':
            # Less than 10 then keep 1 decimal place
            value = "{:.1f}{}".format(n, unit)
            return value
        if round(n) < 1000:
            # Less than 4 digits so use this
            value = "{}{}".format(round(n), unit)
            return value
        base *= 1024
    value = "{}{}".format(round(n), unit)
    return value
