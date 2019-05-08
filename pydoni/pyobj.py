def dictSApply(func, d):
    """
    Apply function to each terminal element of a dictionary.
    Args
        func (function): name of function to apply.
        d    (dict)    : dictionary to apply `func` to.
    Returns
        dict
    """
    if (isinstance(d, str)):
        return func(d)
    elif (isinstance(d, dict)):
        return { key : dictSApply(func, d[key]) for key in d }
    elif (isinstance(d, list)):
        return [ dictSApply(func, val) for val in d ]

class DoniDict(dict):
    """
    Dictionary class with recursive 'get' method.
    Args
        mydict (dict): dictionary to convert to DoniDict
    """
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
    """
    Print the current time formatted as a string.
    Args
        stripchars (bool): If True, strip dashes and colons from datetime string (YYYYMMDD_HHMMSS). If False, return as YYYY-MM-DD HH:MM:SS.
    Returns
        str
    """
    import datetime
    if stripchars:
        return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    else:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def sysdate(stripchars=False):
    """
    Print the current date formatted as a string.
    Args
        stripchars (bool): If True, strip dashes and colons from date string (YYYYMMDD). If False, return as YYYY-MM-DD.
    Returns
        str
    """
    import datetime
    if stripchars:
        return datetime.datetime.now().strftime("%Y%m%d")
    else:
        return datetime.datetime.now().strftime("%Y-%m-%d")


def assert_len(varlist, varnames):
    """
    Ensure lengths of variables are equal, otherwise throw an error
    Args
        varlist (list): list of lists to test the lengths of
        varnames (list): list of names of variables (used for verbose output)
    Returns
        nothing
    """
    import click
    from pydoni.vb import echo
    lengths = [len(x) for x in varlist]
    if len(set(lengths)) > 1:
        echo("Unequal variable lengths: {}. Respective lengths are {}".format(
            ', '.join("'" + click.style(item,      fg='red', bold=True) + "'" for item in varnames),
            ', '.join("'" + click.style(str(item), fg='red', bold=True) + "'" for item in lengths)),
        fn_name='assert_len', abort=True)


def user_select_from_list(lst, indent=0, msg='Please make a selection (hyphen-separated range ok): ', allow_range=True):
    """
    Prompt user to make a selection from a list. Supports comma- and hyphen-separated selection.
    For example, a user may select elements from a list as:
        1-3, 5, 10-15, 29  ->  [1,2,3,5,10,11,12,13,14,15,29]
    Args
        lst         (list): list of selections
        indent      (int) : indentation level of all items of `lst`
        msg         (str) : [optional] custom message to print instead of default
        allow_range (bool): if True, allow user to make multiple selections
    Returns
        slice of list
    """
    import re
    from pydoni.vb import echo
    
    # Add indent to each element of `lst`
    if indent > 0:
        tab = '\t' * indent
        for i, item in enumerate(lst):
            print('{}({}) {}'.format(tab, str(i+1), item))
    
    # User must make a valid selection. If selection is invalid, re-run through this while loop.
    invalid = True
    while invalid:
        # Get user input
        uin_raw = input(msg + ': ' if not msg.rstrip().endswith(':') else msg)

        # Test if user input is valid. User input must consist only of numbers, commas and/or hyphens
        if not uin_raw.replace('-', '').replace(',', '').replace(' ', '').strip().isdigit():
            echo('User input must consist only of numbers, commas and/or hyphens', error=True)
            invalid = True
            continue

        # User input is range (valid)
        if allow_range:
            # Parse user input to individual numerical selections
            uin = uin_raw.split(',')
            selection = []
            for x in uin:
                x = x.strip()
                if '-' in x:
                    selection.append(
                        list(range(int(x.split('-')[0]), int(x.split('-')[1])+1)))
                else:
                    selection.append([int(x)])
            selection = list(set([item for sublist in selection for item in sublist]))
            assert all([isinstance(x, int) for x in selection])

            # Test if range is truly within the length of `lst`
            if selection[len(selection)-1] > len(lst) or selection[0] < 1:
                # Range is outside of true length of `lst`
                echo('Entry must be between {} and {}'.format('1', str(len(lst))), error=True)
                invalid = True
                continue
            
            else:
                # Range is valid, slice list at selection
                val = [lst[i-1] for i in selection]
                break

        elif re.search(r'^(\d+)$', uin):
            # User input is single selection (valid)
            uin = int(uin)
            if uin < 1 or uin > len(lst):
                echo('Entry must be between {} and {}'.format('1', str(len(lst))), error=True)
                invalid = True
                continue
            return lst[uin-1]
        
        else:
            # User input is invalid (not a single selection or a range selection)
            echo("Invalid entry. Must match either '\d+' or '\d+-\d+'", error=True)
            invalid = True
            continue
    
    return val


def fmt_seconds(time_in_sec, units='auto', round_digits=4):
    """
    Format time in seconds to a custom string.
    Args
        time_in_sec  (int): time in seconds to format
        units        (str): target units to format seconds as, one of ['auto', 'seconds', 'minutes', 'hours', 'days']
        round_digits (int): number of digits to round to
    Return
        dict(
            units = <str>,
            value = <int>
        )
    """
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


def listmode(lst):
    """
    Get the most frequently-occurring value in a list.
    Args
        lst (list): list to get mode from
    Returns
        str or int
    """
    return max(set(lst), key=lst.count)


def dict_filter(d, keys):
    """
    Filter dictionary by list of keys.
    Args
        d    (dict): dictionary to filter
        keys (list): key names to filter on
    """
    return {k.lower().replace(' ', '_'): v for k, v in d.items() if k.lower().replace(' ', '_') in keys}


def cap_nth_char(string, n):
    """
    Capitalize the Nth character of a string. If 'n' is out of range, return original string.
    Args
        string (str): string to consider
        n      (int): position to capitalize letter in `string`
    Return
        str
    """
    if n >= len(string):
        return string
    return string[:n] + string[n].capitalize() + string[n+1:]


def replace_nth_char(string, n, replacement):
    """
    Capitalize the Nth character of a string. If 'n' is out of range, return original string.
    Args
        string      (str)       : string to consider
        n           (int)       : position to capitalize letter in `string`
        replacement (str or int): string or integer to replace nth char with
    Return
        str
    """
    if n >= len(string):
        return string
    return string[:n] + str(replacement) + string[n+1:]


def insert_nth_char(string, n, char):
    """
    Capitalize the Nth character of a string. If 'n' is out of range, return original string.
    Args
        string (str)       : string to consider
        n      (int)       : position to capitalize letter in `string`
        char   (str or int): string or integer to insert at nth position
    Return
        str
    """
    if n >= len(string):
        return string
    return string [:n] + str(char) + string[n:]


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
