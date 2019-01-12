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

def validatelen(varlist, varnames):  # Ensure lengths of variables are equal, otherwise error
    import click
    from PyFunctions import echoError
    lengths = [len(x) for x in varlist]
    if len(set(lengths)) > 1:
        echoError("Unequal variable lengths: {}. Respective lengths are {}".format(
            ', '.join("'" + click.style(item,      fg='red', bold=True) + "'" for item in varnames),
            ', '.join("'" + click.style(str(item), fg='red', bold=True) + "'" for item in lengths)),
        fn_name='validatelen', abort=True)

def userSelectFromList(lst, indent=0, msg=None, allow_range=True):
    import re
    from PyFunctions import echo
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

