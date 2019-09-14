import re
import datetime
from os.path import expanduser, splitext


class DoniDict(dict):
    """
    Dictionary class with recursive 'get' method.
    
    Arguments:
        mydict {dict} -- dictionary to convert to DoniDict
    """

    def __init__(self, mydict):
        self.mydict = dictSApply(expanduser, mydict)
    
    def rget(self, *args, **kwargs):
        default = kwargs.get('default')
        cursor = self.mydict
        for a in args:
            if cursor is default: break
            cursor = cursor.get(a, default)
        return cursor


def dictSApply(func, d):
    """
    Apply function to each terminal element of a dictionary.
    
    Arguments:
        func {function} -- name of function to apply.
        d {dict} -- dictionary to apply `func` to.

    Returns:
        {dict}
    """
    if (isinstance(d, str)):
        return func(d)
    elif (isinstance(d, dict)):
        return { key : dictSApply(func, d[key]) for key in d }
    elif (isinstance(d, list)):
        return [ dictSApply(func, val) for val in d ]


def systime(stripchars=False):
    """
    Print the current time formatted as a string.
    
    Arguments:
        stripchars {bool} -- if True, strip dashes and colons from datetime string and return YYYYMMDD_HHMMSS. If False, return as YYYY-MM-DD HH:MM:SS
    
    Returns:
        {str}
    """
    if stripchars:
        return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    else:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def sysdate(stripchars=False):
    """
    Print the current date formatted as a string.
    
    Arguments:
        stripchars {bool} -- If True, strip dashes and colons from date string as YYYYMMDD If False, return as YYYY-MM-DD.
    
    Returns:
        str
    """
    if stripchars:
        return datetime.datetime.now().strftime("%Y%m%d")
    else:
        return datetime.datetime.now().strftime("%Y-%m-%d")


def assert_len(varlist, varnames=None):
    """
    Ensure lengths of variables are equal, otherwise throw an error
    
    Arguments:
        varlist {list} -- list of lists to test the lengths of

    Keyword Arguments:
        varnames {list} -- list of names of variables (used for verbose output) (default: {None})

    Returns:
        {bool}
    """

    assert isinstance(varlist, list)

    lengths = [len(x) for x in varlist]
    
    if len(set(lengths)) > 1:
        if varnames is not None:
            assert length(varlist) == length(varnames)
            echo("Unequal variable lengths: {}. Respective lengths are {}".format(
                ', '.join("'" + click.style(item,      fg='red', bold=True) + "'" for item in varnames),
                ', '.join("'" + click.style(str(item), fg='red', bold=True) + "'" for item in lengths)),
                fn_name='assert_len', abort=True)
            return False
        else:
            echo("At least one element of 'varlist' is of unequal length", fn_name='assert_len', abort=True)
            return False
    else:
        return True


def user_select_from_list(
    lst,
    indent=0,
    msg='Please make a selection (hyphen-separated range ok): ',
    allow_range=True
    ):
    """
    Prompt user to make a selection from a list. Supports comma- and hyphen-separated selection.
    For example, a user may select elements from a list as:
        1-3, 5, 10-15, 29  ->  [1,2,3,5,10,11,12,13,14,15,29]
    
    Arguments:
        lst {list} -- list of selections

    Keyword Arguments:
        indent {int} -- indentation level of all items of `lst` (default: {0})
        msg {str} -- custom message to print instead of default (default: {'Please make a selection (hyphen-separated range ok): '})
        allow_range {bool} -- if True, allow user to make multiple selections (default: {True})

    Returns:
        {list} -- slice of `lst`
        {str} -- element of `lst`
    """
    
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

        elif re.search(r'^(\d+)$', uin_raw):
            # User input is single selection (valid)
            uin = int(uin_raw)
            if uin < 1 or uin > len(lst):
                echo('Entry must be between {} and {}'.format('1', str(len(lst))), error=True)
                invalid = True
                continue
            return lst[uin-1]
        
        else:
            # User input is invalid (not a single selection or a range selection)
            echo("Invalid entry. Must match either '\\d+' or '\\d+-\\d+'", error=True)
            invalid = True
            continue
    
    return val


def fmt_seconds(time_in_sec, units='auto', round_digits=4):
    """
    Format time in seconds to a custom string.
    
    Arguments:
        time_in_sec {int} -- time in seconds to format

    Keyword Arguments:
        units {str} -- target units to format seconds as, one of ['auto', 'seconds', 'minutes', 'hours', 'days'] (default: {'auto'})
        round_digits {int} -- number of digits to round to (default: {4})
    Return:
        {dict} -- dict(
            units = {str},
            value = {int}
        )
    """

    assert units in ['auto', 'seconds', 'minutes', 'hours', 'days']

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

    return dict(zip(['units', 'value'], [time_measure, time_diff]))


def listmode(lst):
    """
    Get the most frequently occurring value in a list.
    
    Arguments:
        lst {list} -- list to get mode from

    Returns:
        {str} or {int}
    """
    return max(set(lst), key=lst.count)


def dict_filter(d, keys):
    """
    Filter dictionary by list of keys.
    
    Arguments:
        d {dict} -- dictionary to filter
        keys {list} -- key names to filter on
    """
    return {k.lower().replace(' ', '_'): v for k, v in d.items() if k.lower().replace(' ', '_') in keys}


def cap_nth_char(string, n):
    """
    Capitalize the Nth character of a string. If 'n' is out of range, return original string.
    
    Arguments:
        string {str} -- string to consider
        n {int} -- position to capitalize letter in `string`
    
    Returns:
        {str}
    """
    if n >= len(string):
        return string
    return string[:n] + string[n].capitalize() + string[n+1:]


def replace_nth_char(string, n, replacement):
    """
    Capitalize the Nth character of a string. If 'n' is out of range, return original string.
    
    Arguments:
        string {str} -- string to consider
        n {int} -- position to capitalize letter in `string`
        replacement {str} or {int} -- string or integer to replace nth char with
    
    Returns:
        {str}
    """
    if n >= len(string):
        return string
    return string[:n] + str(replacement) + string[n+1:]


def insert_nth_char(string, n, char):
    """
    Capitalize the Nth character of a string. If 'n' is out of range, return original string.
    
    Arguments:
        string {str} -- string to consider
        n {int} -- position to capitalize letter in `string`
        char {str} or {int} -- string or integer to insert at nth position
    
    Returns:
        {str}
    """
    if n >= len(string):
        return string
    return string [:n] + str(char) + string[n:]


def human_filesize(nbytes: int) -> str:
    """
    Convert number of bytes to human-readable filesize string.

    Arguments:
        nbytes {int} -- number of bytes to format as string

    Returns:
        {str}

    Original Source:
        https://stackoverflow.com/questions/5194057/better-way-to-convert-file-sizes-in-python
    """
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


def split_at(lst, idx):
    """
    Split a list at a given index or list of indices.
    
    Arguments:
        lst {list} -- list to split
        idx {int} or {list} -- indexes to split the list at

    Returns:
        {list} -- list of lists
    """
    return [lst[i:j] for i, j in zip([0] + idx, idx + [None])]


def duplicated(lst):
    """
    Return list of boolean values indicating whether each item in a list
    is a duplicate of a previous item.
    
    Arguments:
        lst {list} -- a list to test for duplicates

    Returns:
        {list}
    """
    dup_ind = []
    for i, item in enumerate(lst):
        tmplist = lst.copy()
        del tmplist[i]
        if item in tmplist:
            # Test if this is the first occurrence of this item in the
            # list. If so, do not count as duplicate, as the first item
            # in a set of identical items should not be counted as
            # a duplicate
            first_idx = min(
                [i for i, x in enumerate(tmplist) if x == item])
            if i != first_idx:
                dup_ind.append(True)
            else:
                dup_ind.append(False)
        else:
            dup_ind.append(False)
    return dup_ind


def ddml_to_md(fname):
    """
    Convert a text file formatted in DDML (Dapper Doni Markup Language) to Markdown.
    
    Arguments:
        fname {str} -- path to textfile formatted in DDML
        
    Returns:
        nothing
    """

    with open(fname, 'r') as f:
        text = f.read().split('\n')

    # Attempt to parse the type of each line
    line_type = []
    for x in text:
        if re.match(r'^\d{4}$', x) and x.startswith('20'):
            line_type.append('year')
        elif re.match(r'^ {2}\d{2}$', x) and \
            x.strip() in [str(x).rjust(2).replace(' ', '0') for x in range(1, 13)]:
            line_type.append('month')
        elif re.match(r'^ {4}\d{2}$', x) and \
            x.strip() in [str(x).rjust(2).replace(' ', '0') for x in range(1, 32)]:
            line_type.append('day')
        else:
            line_type.append('normal')

    # Check top two lines for a DDML heading in format "HEADING_TEXT\n============"
    if re.match('^=+$', text[1]):
        line_type[0] = 'doc_title'
        del text[1]
        del line_type[1]

    # Get any DDML tags (<em>, <li>, <h>, <title>)
    tag = []
    ddml_tags = ['em', 'li', 'h', 'title']
    for x in text:
        present_tag = 'none'
        for ddml_tag in ddml_tags:
            if '<' + ddml_tag + '>' in x:
                present_tag = ddml_tag
        tag.append(present_tag)

    # Get indent level for each 
    indent_level = []
    for x in text:
        spaces = re.search('^ +', x)
        if spaces:
            spaces = spaces.group(0)
            idt = int(len(spaces)/2)
            if idt > 0:
                idt = idt - 1
            indent_level.append(idt)
        else:
            indent_level.append(0)


    # Convert DDML to MD

    md = []
    for indent, x in list(zip(indent_level, text)):
        ws = '    ' * indent
        md.append(ws + x.strip())

    year_loc = [i for i, x in enumerate(line_type) if x == 'year']
    if len(year_loc):
        for i in year_loc:
            md[i] = '\n### ' + md[i]

    month_loc = [i for i, x in enumerate(line_type) if x == 'month']
    if len(month_loc):
        for i in month_loc:
            md[i] = '* ' + re.sub(r'^ +\*', '', md[i].strip())

    day_loc = [i for i, x in enumerate(line_type) if x == 'day']
    if len(day_loc):
        for i in day_loc:
            md[i] = ' '*4 + '* ' + re.sub(r'^ +\*', '', md[i].strip())

    doc_title_loc = [i for i, x in enumerate(line_type) if x == 'doc_title']
    if len(doc_title_loc):
        for i in doc_title_loc:
            md[i] = '# ' + md[i].replace('*', '').strip()

    # Line by line replacements
    md_final = []
    for line in md:
        line = line.replace('->', '&rarr;')
        line = line.replace('_', '\_')
        bullet = re.match(r'^ +\* ', line)
        if bullet is not None:
            bullet = bullet.group(0)
            text = line.replace(bullet, '')
            line = bullet + text.replace('*', '\*')
        md_final.append(line)

    # DDML tags
    for i, tg in enumerate(tag):
        if tg in 'em':
            md_final[i] = re.sub(r'^( +\* )(.*)( <em>)$', r'\1**\2**', md_final[i])  # Markdown: bold
            md_final[i] = md_final[i].replace('\*', '*')
        elif tg == 'li':
            md_final[i] = md_final[i].replace(' <li>', '')
        elif tg in ['h', 'title']:
            md_final[i] = re.sub(r'^( +\*? )(.*)( <(h|title)>)$', r'\1*\2*', md_final[i])  # Markdown: italic
            md_final[i] = md_final[i] .replace('\*', '*')

    outfile = splitext(fname)[0] + '.md'
    with open(outfile, 'w') as f:
        for line in md_final:
            f.write(line + '\n')


def make_md_list(string, li_type, tab_size=4):
    """
    Add markdown bullets to each element of markdown string, separated by \n.
    
    Arguments:
        string {char} -- character string in markdown
        li_type {char} -- type of list item, one of "1" (ordered list), or "-" or "*" (unordered list)
    
    Keyword Arguments:
        tab_size {int} -- size of whitespace indentation (default: {4})

    Returns:
        {str}
    """


    # Replace tabs with spaces
    indent = ' ' * tab_size
    string = string.replace('\\t', indent)
    string = string.replace('\t', indent)

    # Add bullets
    lst = re.split(r'\n|\\n', string)
    if li_type == '1':
        bullets = [str(x) + '.' for x in list(range(1, len(lst)+1))]
    else:
        bullets = list(li_type * len(lst))
    indentation = [re.sub(r'^( *).*', r'\1', x) for x in lst]
    lst = [x.strip() for x in lst]
    md_list = ['{}{} {}'.format(a, b, c) for a, b, c in zip(indentation, bullets, lst)]

    return '\n'.join(md_list)


def markdown_toc(md_fpath, li_type):
    """
    Generate Markdown table of contents as character string given a Markdown file.
    
    Arguments:
        md_fpath {str} -- path to Markdown file
        li_type {str} -- type of list item, one of "1" (ordered list), or "-" or "*" (unordered list)

    Returns:
        {str} -- Markdown TOC string
    """


    with open(md_fpath, 'r') as f:
        md = f.readlines()

    # Get lines that correspond to headings
    h = [x for x in md if re.match(r'^#+', x)]
    
    # Indent each item according to heading level (# = 0, ## = 1, ### = 2, ...)
    indent = '\t'

    # Add "Table of Contents" item as heading level 2
    first_h2 = [i for i, x in enumerate(h) if x.startswith('## ')]
    if len(first_h2):
        # There is an H2, so put TOC item above that one
        first_h2 = min(first_h2)
        h = h[:first_h2] + ['## Table of Contents'] + h[first_h2:]
    else:
        # There is no H2, so put TOC item at the very top
        h = ['## Table of Contents'] + h

    # Add indent and paste into string
    h = [x.replace('#', '', 1).strip() for x in h]
    h = [x.replace('#', indent) for x in h]
    h = [re.sub(r'^(\t+) ', r'\1', x) for x in h]  # Remove space between last \t and the text
    h = '\n'.join(h)

    # Add bullet to each item
    h_bullets = make_md_list(h, li_type=li_type, tab_size=4).split('\n')

    # Format each item as [TEXT](#text)
    pat = r"^( *)(-|\*|\d+)( )(.*)$"
    element_names = [re.sub(pat, r'\4', x) for x in h_bullets]
    element_names = [x.replace('(', '').replace(')', '').replace('[', '') \
        .replace(']', '').replace(' ', '-').replace(':', '').lower() for x in element_names]
    h_bullets = [re.sub(pat, r'\1\2\3[\4]', x) for x in h_bullets]
    h_toc = ['{}(#{})'.format(a, b) for a, b in zip(h_bullets, element_names)]

    # Add table of contents H2
    h_toc = ['## Table of Contents', ''] + h_toc
    
    return '\n'.join(h_toc)


def naturalsort(lst):
    """
    Sort a list with numeric elements, numerically.

    Arguments:
        lst {list} -- list to sort

    Returns:
        {list}

    Source:
        https://stackoverflow.com/questions/5967500/how-to-correctly-sort-a-string-with-a-number-inside
    """
    def atoi(text):
        return int(text) if text.isdigit() else text

    def natural_keys(text):
        '''
        alist.sort(key=natural_keys) sorts in human order
        http://nedbatchelder.com/blog/200712/human_sorting.html
        (See Toothy's implementation in the comments)
        '''
        return [ atoi(c) for c in re.split(r'(\d+)', text) ]

    return sorted(lst, key=natural_keys)


def test(value, dtype):
    """
    Test if a value is an instance of type `dtype`.

    Arguments:
        value {str} -- value to test
        dtype {str} -- one of ['bool', 'date', 'int', 'float', 'str']

    Returns:
        {bool}
    """
    
    assert dtype in ['bool', 'date', 'int', 'float', 'str']

    try:
        if dtype == 'bool':
            assert value.lower() in ['true', 'false']
        elif dtype == 'date':
            test = datetime.strptime(value, '%Y-%m-%d')
        elif dtype == 'int':
            test = int(value)
        elif dtype == 'float':
            test = float(value)
        elif dtype == 'str':
            test = str(value)
        return True
    except:
        return False


def get_input(msg='Enter input', mode='default'):
    """
    Get user input, optionally of specified format.

    Keyword Arguments:
        msg {str} -- message to print to console (default: {'Enter input'})
        mode {str} -- apply filter to user input, one of ['bool', 'date', 'int', 'float', 'str'] (default: {'default'})

    Returns:
        {str}
    """

    assert mode in ['default', 'bool', 'date', 'int', 'float', 'str']

    # Add suffix based on mode
    msg = re.sub(r': *$', '', msg).strip()
    if mode == 'bool':
        msg = msg + ' ' + '(y/n): '
    elif mode == 'date':
        msg = msg + ' ' + '(YYYY-MM-DD): '
    else:
        msg == msg + ' : '

    uin_raw = input(msg)

    if mode == 'bool':
        while uin_raw.lower() not in ['y', 'yes', 'n', 'no']:
            uin_raw = input("Must enter 'y' or 'n': ")
        if uin_raw.lower() in ['y', 'yes']:
            return True
        else:
            return False
    elif mode == 'date':
        while not is_date(uin_raw):
            uin_raw = input("Must enter valid date in format 'YYYY-MM-DD': ")

    return uin_raw


from pydoni.vb import echo
