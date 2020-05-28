# -*- coding: utf-8 -*-

import pydoni
import pydoni.vb
import logging
import sys

# Logger commands for every function and class in module -------------------------------------------

# Functions
"""
    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())
"""

# Classes
"""
        self.logger = pydoni.logger_setup(
            name=pydoni.what_is_my_name(classname=self.__class__.__name__, with_modname=True),
            level=pydoni.modloglev)
        self.logger.logvars(locals())
"""

# Module variables ---------------------------------------------------------------------------------

modloglev = logging.WARN

# Module classes -----------------------------------------------------------------------------------

class ExtendedLogger(logging.Logger):
    """
    Extend logging.Logger.

    :param name: name of logger
    :type name: str
    :param level: logging level
    :type level: int
    """

    def __init__(self, name, level=logging.NOTSET):

        import threading

        self._count = 0
        self._countLock = threading.Lock()

        return super(ExtendedLogger, self).__init__(name, level)

    def var(self, varname, value, include_modules=True, include_extended_logger=True):
        """
        Extend .debug() method to log variable names, dtypes and values in shorthand.

        :param varname: name of variable to log
        :type varname: str
        :param value: variable to log
        :type value: any
        :param include_modules: log modules as any other variable
        :type include_modules: bool
        :param include_extended_logger: log instances of this class as any other variable
        :type include_extended_logger: bool
        :return: debug message
        :rtype: logging.logger.debug
        """
        dtype = value.__class__.__name__
        value = str(value)
        msg = 'Var {varname} {{{dtype}}}: {value}'.format(**locals())

        if dtype == 'module' and not include_modules:
            return None

        if 'ExtendedLogger' in dtype and not include_extended_logger:
            return None

        return super(ExtendedLogger, self).debug(msg)

    def logvars(self, var_dict):
        """
        Iterate over dictionary and call `self.var` on each.

        :param var_dict: dictionary of varname: value pairs, may be output of `locals()`
        :type var_dict: dict
        """
        for varname, value in var_dict.items():
            self.var(varname, value, include_modules=False, include_extended_logger=False)


# Module functions ---------------------------------------------------------------------------------

def what_is_my_name(classname=None, with_modname=True):
    """
    Return name of function that calls this function. If called from a
    classmethod, include classname before classmethod in output string.

    :param with_modname {bool} -- append module name to beginning of function name (True)
    :return: {str}
    """
    import inspect

    lst = []
    funcname = inspect.stack()[1][3]

    if with_modname:
        modulename = inspect.getmodule(inspect.stack()[1][0]).__name__
        if modulename != '__main__':
            lst += [modulename]

    if isinstance(classname, str):
        lst += [classname]

    lst += [funcname]
    return '.'.join(lst)


def logger_setup(name='root', level=modloglev):
    """
    Define an identical logger object for all pydoni submodules.

    :param name: desired logger name
    :type name: str
    :param level: desired logging.Logger level
    :type level: str
    """

    logging.setLoggerClass(ExtendedLogger)
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger_fmt = '%(asctime)s : %(levelname)s : %(name)s : %(message)s'

        formatter = logging.Formatter(logger_fmt)
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        logger.setLevel(modloglev)

    return logger


def syscmd(cmd, encoding=''):
    """
    Runs a command on the system, waits for the command to finish, and then
    returns the text output of the command. If the command produces no text
    output, the command's return code will be returned instead.

    :param cmd: command string to execute
    :type cmd: str
    :param encoding: [optional] name of decoding to decode output bytestring with
    :type encoding: str
    :return: interned system output {str}, or returncode {int}
    :rtype: str or int
    """

    import subprocess

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    p = subprocess.Popen(
        cmd,
        shell     = True,
        stdin     = subprocess.PIPE,
        stdout    = subprocess.PIPE,
        stderr    = subprocess.STDOUT,
        close_fds = True)

    logger.debug('Waiting...')
    p.wait()
    logger.debug('The Waiting is the hardest part')
    output = p.stdout.read()

    logger.var('output', output)
    logger.var('p.returncode', p.returncode)

    if len(output) > 1:
        if encoding:
            return output.decode(encoding)
        else:
            return output

    return p.returncode


def listfiles(
        path='.',
        pattern=None,
        ext=None,
        full_names=False,
        recursive=False,
        ignore_case=True,
        include_hidden_files=False):
    """
    List files in a given directory.

    :param path: directory path in which to search for files
    :type path: str
    :param pattern: if specified, filter resulting files by matching regex pattern
    :type pattern: str
    :param ext: extention or list of extensions to filter resulting files by
    :type ext: str
    :param full_names: return full filepaths
    :type full_names: bool
    :param recursive: search recursively down the directory tree
    :type recursive: bool
    :param ignore_case: do not consider case in when filtering for `pattern` parameter
    :type ignore_case: bool
    :param include_hidden_files: include hidden files in resulting file list
    :type include_hidden_files: bool
    :return: list of files present at directory
    :rtype: list
    """
    import os
    import re

    owd = os.getcwd()
    os.chdir(path)

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    if recursive:
        files = []
        for root, dirs, filenames in os.walk('.'):
            for f in filenames:
                files.append(os.path.join(root, f).replace('./', ''))

    else:
        files = [f for f in os.listdir() if os.path.isfile(f)]

    if not include_hidden_files:
        files = [f for f in files if not os.path.basename(f).startswith('.')]

    if pattern is not None:
        if ignore_case:
            files = [f for f in files if re.search(pattern, f, re.IGNORECASE)]
        else:
            files = [f for f in files if re.search(pattern, f)]

    if ext:
        ext = [x.lower() for x in pydoni.ensurelist(ext)]
        ext = ['.' + x if not x.startswith('.') else x for x in ext]
        files = [x for x in files if os.path.splitext(x)[1].lower() in ext]

    if full_names:
        path_expand = os.getcwd() if path == '.' else path
        files = [os.path.join(path_expand, f) for f in files]

    os.chdir(owd)
    return sorted(files)


def listdirs(path='.', pattern=None, full_names=False, recursive=False):
    """
    List subdirectories in a given directory.

    :param path: directory path in which to search for subdirectories
    :type path: str
    :param pattern: if specified, filter resulting dirs by matching regex pattern
    :type pattern: str
    :param full_names: return full relative directory path
    :type full_names: bool
    :param recursive: search recursively down directory tree
    :type recursive: bool
    :return: list of subdirectories
    :rtype: list
    """

    import os
    import re

    owd = os.getcwd()
    os.chdir(path)

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    if recursive:
        dirs = []
        for root, subdirs, filenames in os.walk('.'):
            for subdir in subdirs:
                dirs.append(os.path.join(root, subdir).replace('./', ''))
    else:
        dirs = sorted(next(os.walk(path))[1])

    if full_names:
        path_expand = os.getcwd() if path == '.' else path
        dirs = [os.path.join(path_expand, dname) for dname in dirs]

    if pattern is not None:
        dirs = [d for d in dirs if re.match(pattern, d)]

    os.chdir(owd)
    return sorted(dirs)


def ensurelist(val):
    """
    Accept a string or list and ensure that it is formatted as a list. If `val` is not a list,
    return [va]. If `val` is already a list, return as is.

    :param val: value to coerce to list
    :type val: any
    """
    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())
    return [val] if not isinstance(val, list) else val


def print_apple_ascii_art(by_line=False, by_char=False, sleep=0):
    """
    Print Apple WWDC 2016 ASCII artwork logo.

    :param by_line: print out logo by line instead of all at once
    :type by_line: str
    :param by_line: print out logo by character instead of all at once
    :type by_char: str
    :param sleep: time delay between printing line or character if either set to True
    :type sleep: int or float
    """

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    ascii_string = """                                  -·\n                              _/=\:<\n                             .#/*let}\n                           //as\@#:~/\n                          try()|:-./\n                         *~let:>@f#\n                         </>#@~*/\n                        (+!:~/+/\n                        /={+|\n          _.:+*as=._           _.]@~let[._\n       .*()/if{@[[-#>\=.__.<>/#{*+/@*/for=*~.\n      /-(#]:.(var/@~as/@</>\]=/<if[/*:/<try@\~\n     [:/@#</>}#for=\>.<:try#>=\*.if(var<<.+_:#(=.\n   #do()=*:.>as//@[]-./[#=+)\(var/@<>[]:-##~/*>\n  =*:/([<.//>*~/]\+/_/([\<://:_*try/<:#if~do-:\n @#/*-:/#do.i@var=\<)]#>/=\>\<for#>|*:try=\"</\n :/./@#[=#@-asl#:/-i@if.>#[.)=*>/let\{\}</):\~\n(@+_let#do/.@#=#>[/]#let=#or@\=<()~if)*<)\)\nfor):/=]@#try:</=*;/((+do_{/!\\"(@-/((:@>).*}\n/@#:@try*@!\\as=\>_@.>#+var>_@=>#+-do)=+@#>(\n{}:/./@#=do]>/@if)=[/[!\<)#)try+*:~/#).=})=\ntry@#_<(=<i>do#.<}@#}\\=~*:/().<))_+@#()+\>\n *:#for@:@>):/#<\=*>@\\var_}#|[/@*-/.<:if#/-\\\n =<)=~\(-for>ii@if*=*+#as\<)*:#for@f#)try+}).\n [for()=.[#in=*:as=\>_@-.>#do/:/([+var)=+@#]]=\n  /@[as:=\+@#]=:/let[(=\<_)</@->#for()=))#>in>)_\n  *)\{}/*<var/(>;<+/:do#/-)<\(:as/>)(})_+=<(for+=\.\n   do=~\@#=\><<-))_|@#(])/)_+@let]:[+#\=@/if[#()[=\n    =<]).if|/.=*@var<@:/(-)=*:/#)=*>@#var(<(]if):*\n    {/+_=@#as}#:/-i@if>in=@#{#in=>()@>](@#<{:})->\n     \.=let_@<)#)_=\<~#_)@}+@if#-[+#\|=@#~try/as\n       var<:))+-ry-#»+_+=)>@#>()<?>var)=~<+.-/\n        +@>#do(as)*+[#]=:/(/#\<)if).+let:@(.#\"\n         {}</().try()##/as<){*-</>}](as*>-/<\n           <()if}*var(<>.-\"_\"~.let>#[.)=*>/\n             {}<as:\"            \"*)}do>\n"""

    if by_line or by_char:
        import time

        if by_line and by_char:
            logger.warning('Both `by_line` and `by_char` specified. Prioritizing `by_line`.')

        if by_line:
            lines = ascii_string.split('\n')
            for line in lines:
                print(line)
                if sleep > 0:
                    time.sleep(sleep)

        elif by_char:
            for char in ascii_string:
                print(char, end='', flush=True)
                if sleep > 0:
                    time.sleep(sleep)
    else:
        print(ascii_string)


def systime(stripchars=False):
    """
    Get the current datetime formatted as a string.

    :param stripchars: strip dashes and colons from datetime string and return YYYYMMDD_HHMMSS
    :type stripchars: bool
    :return: system time formatted as string
    :rtype: str
    """
    from datetime import datetime

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    fmt = "%Y%m%d_%H%M%S" if stripchars else "%Y-%m-%d %H:%M:%S"
    return datetime.now().strftime(fmt)


def sysdate(stripchars=False):
    """
    Get the current date formatted as a string.

    :param stripchars: strip dashes and colons from datetime string and return YYYYMMDD
    :type stripchars: bool
    :return: system time formatted as string
    :rtype: str
    """
    from datetime import datetime

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    fmt = "%Y%m%d" if stripchars else "%Y-%m-%d"
    return datetime.now().strftime(fmt)


def naturalsort(lst):
    """
    Sort a list with numeric elements, numerically.
    Source: https://stackoverflow.com/questions/5967500/how-to-correctly-sort-a-string-with-a-number-inside

    :param lst: list to sort
    :type lst: list
    :return: list in naturally sorted order
    :rtype: list
    """

    import re

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    def atoi(text):
        return int(text) if text.isdigit() else text

    def natural_keys(text):
        """
        alist.sort(key=natural_keys) sorts in human order
        http://nedbatchelder.com/blog/200712/human_sorting.html
        (See Toothy's implementation in the comments)
        """
        return [atoi(c) for c in re.split(r'(\d+)', text)]

    return sorted(lst, key=natural_keys)


def dictSApply(func, d):
    """
    Apply function to each terminal element of a dictionary.

    :param func: name of function to apply.
    :type func: function
    :param d:dictionary to apply `func` to.
    :type d: dict
    :return: dictionary, list or function result of function applied to each terminal element of `d`
    :rtype: dict, list or any
    """

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    if isinstance(d, str):
        return func(d)
    elif isinstance(d, dict):
        return { key : dictSApply(func, d[key]) for key in d }
    elif isinstance(d, list):
        return [ dictSApply(func, val) for val in d ]


def assert_len(varlist, varnames=None):
    """
    Ensure lengths of variables are equal, otherwise throw an error

    :param varlist: list of lists to test the lengths of
    :type varlist: list
    :param varnames: list of names of variables (used for verbose output)
    :type varnames: list
    :rtype: bool
    """
    import click

    assert isinstance(varlist, list)

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    lengths = [len(x) for x in varlist]

    if len(set(lengths)) > 1:
        if varnames is not None:
            assert len(varlist) == len(varnames)
            logger.error("Unequal variable lengths: {}. Respective lengths are {}".format(
                ', '.join("'" + click.style(item, fg='red', bold=True) + "'" for item in varnames),
                ', '.join("'" + click.style(str(item), fg='red', bold=True) + "'" for item in lengths)))
            return False
        else:
            logger.error("At least one element of 'varlist' is of unequal length")
            return False
    else:
        return True


def user_select_from_list(
        lst,
        indent=0,
        msg=None,
        num_adj=0,
        valid_opt=None,
        allow_range=True,
        return_idx=False,
        noprint=False):
    """
    Prompt user to make a selection from a list. Supports comma- and hyphen-separated selection.

    Example:
        A user may select elements from a list as:
        1-3, 5, 10-15, 29  ->  [1,2,3,5,10,11,12,13,14,15,29]

    :param lst:list of items to select from
    :type lst: list
    :param indent: indentation level of all items of `lst`
    :type indent: int
    :param msg: custom message to print instead of default
    :type msg: str
    :param num_adj: numeric adjust for display list
    :type num_adj: int
    :param valid_opt: list of valid options, defaults to `lst`
    :type valid_opt: list
    :param allow_range:allow user to make multiple selections using commas and/or hyphens
    :type allow_range: bool
    :param return_idx: return index of selections in `lst` instead of `lst` items
    :type return_idx: bool
    :param noprint: do not print `lst` to console
    :type noprint: bool
    :return: selected element(s) of `lst`
    :rtype: list item or list, depending on user's selection
    """

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    def get_valid_opt(lst, num_adj):
        valid_opt = []
        for i, item in enumerate(lst):
            valid_opt.append(i + num_adj)
        return valid_opt

    def print_lst(lst, indent, num_adj):
        tab = '  ' * indent
        for i, item in enumerate(lst):
            print('{}({}) {}'.format(tab, str(i + num_adj), item))

    def define_msg(msg, allow_range):
        if msg is None:
            if allow_range is True:
                msg = 'Please make a selection (hyphen-separated range ok)'
            else:
                msg = 'Please make a single selection'
        return msg

    def parse_numeric_input(uin_raw, valid_opt, allow_range, silent=False):
        """
        Parse user numeric input to list. If allow_range is False, then input
        must be a single digit. If not, then user may enter input with hyphen(s)
        and comma(s) to indicate different slices of a list.

        Example:
            From a list of [0, 1, 2, 3, 4, 5] a user might enter
            '0-2,4', which should be translated as [0, 1, 2, 4].
            This function will then return [0, 1, 2, 4].

        :param uin_raw: user raw character input
        :type uin_raw: str
        :param allow_range: allow_range parent funtion flag
        :type allow_range: bool
        :param silent: suppress error messages and just return False if invalid entry entered
        :type silent: bool
        :return: normally a list of parsed numeric input. See example above for details.
        :rtype: list
        """

        def error_func(msg):
            pydoni.vb.echo(msg, error=True)

        # Test that input is valid mix of digits, hyphens and commas only
        if not re.match(r'^(\d|-|,)+$', uin_raw):
            if not silent:
                error_func('Input must consist of digits, hyphens and/or ' \
                    'commas only')
            return False

        if allow_range:
            uin_raw = uin_raw.split(',')
            out = []

            for x in uin_raw:
                if '-' in x:

                    start = x.split('-')[0]
                    if start.strip().isdigit():
                        start = int(start)
                    else:
                        if not silent:
                            error_func("'Start' component '%s' of hyphen-" \
                                "separated range unable to be parsed" % start)
                        return False

                    stop = x.split('-')[1]
                    if stop.strip().isdigit():
                        stop = int(stop) + 1
                    else:
                        if not silent:
                            error_func("'Stop' component '%s' of hyphen-" \
                                "separated range unable to be parsed" % stop)
                        return False

                    if start >= stop:
                        if not silent:
                            error_func("Invalid range '%s'. 'Start' "\
                                "must be >= 'stop'" % x)
                        return False

                    out.append(list(range(start, stop)))

                elif x.strip().isdigit():
                    out.append([int(x)])

                else:
                    if not silent:
                        error_func("Component '%s' could not in " \
                            "valid format" % str(x))
                    return False

            out = list(set([item for sublist in out for item in sublist]))

            oos = []
            for x in out:
                if x not in valid_opt:
                    oos.append(x)
            if len(oos):
                if not silent:
                    error_func("Value{} {} out of valid range {}".format(
                        's' if len(oos) > 1 else '',
                        str(oos),
                        str(valid_opt)))
                return False

            return out

        else:
            if uin_raw.strip().isdigit():
                return [int(uin_raw)]
            else:
                return False

    if not noprint:
        print_lst(lst, indent, num_adj)

    valid_opt = get_valid_opt(lst, num_adj) if not valid_opt else valid_opt
    msg = define_msg(msg, allow_range)

    sel = False
    while sel is False:
        uin_raw = pydoni.get_input(msg)
        sel = parse_numeric_input(uin_raw, valid_opt, allow_range)

    if return_idx:
        return sel[0] if len(sel) == 1 else sel
    else:
        out = [x for i, x in enumerate(lst) if i + num_adj in sel]
        return out[0] if len(out) == 1 else out


def user_select_from_list_inq(lst, msg='Select an option'):
    """
    Use PyInquirer module to prompt user to select an item or items from a list.

    :param lst: options to choose from
    :type lst: list
    :return: selection from list
    :rtype: str (default) or list
    """
    import PyInquirer as inq

    style = inq.style_from_dict({
        inq.Token.QuestionMark: '#E91E63 bold',
        inq.Token.Selected    : '#673AB7 bold',
        inq.Token.Instruction : '',
        inq.Token.Answer      : '#2196f3 bold',
        inq.Token.Question    : ''})

    question = [{
        'type': 'list',
        'name': 'option',
        'message': msg,
        'choices': lst}]

    selection = inq.prompt(question)['option']

    return selection


def fmt_seconds(time_in_sec, units='auto', round_digits=4):
    """
    Format time in seconds to a custom string.

    :param time_in_sec: time in seconds to format
    :type time_in_sec: int
    :param units: target units to format seconds as, one of ['auto', 'seconds', 'minutes', 'hours', 'days']
    :type units: str
    :param round_digits: number of digits to round to
    :type round_digits: int
    :return: dictionary with keys 'units' and 'vale'
    :rtype: dict('units': str, 'value': int or float)
    """

    assert units in ['auto', 'seconds', 'minutes', 'hours', 'days']

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

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

    :param lst: list to get mode from
    :type lst: list
    :return: most frequently-occurring element of list
    :rtype: list item
    """
    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())
    return max(set(lst), key=lst.count)


def dict_filter(d, keys):
    """
    Filter dictionary by list of keys.

    :param d: dictionary to filter
    :type d: dict
    :param keys: key names to filter on
    :type keys: list
    """
    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())
    return {k.lower().replace(' ', '_'): v for k, v in d.items() if k.lower().replace(' ', '_') in keys}


def cap_nth_char(string, n):
    """
    Capitalize the Nth character of a string. If 'n' is out of range, return original string.

    :param string:string to consider
    :type string: str
    :param n:position to capitalize letter in `string`
    :type n: int
    :return: string with character at nth position capitalized
    :rtype: str
    """

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    if n >= len(string):
        return string

    return string[:n] + string[n].capitalize() + string[n+1:]


def replace_nth_char(string, n, replacement):
    """
    Capitalize the Nth character of a string. If 'n' is out of range, return original string.

    :param string:string to consider
    :type string: str
    :param n:position to replace character in `string`
    :type n: int
    :param replacement: string or character to replace nth char with
    :type replacement: int
    :return: string with character at nth position replaced with `replacement`
    :rtype: str
    """

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    if n >= len(string):
        return string

    return string[:n] + str(replacement) + string[n+1:]


def insert_nth_char(string, n, char):
    """
    Capitalize the Nth character of a string. If 'n' is out of range, return original string.

    :param string:string to consider
    :type string: str
    :param n:position to insert character in `string`
    :type n: int
    :param char: string or character to insert at nth position
    :type char: int
    :return: string with character at nth position inserted
    :rtype: str
    """

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    if n >= len(string):
        return string

    return string [:n] + str(char) + string[n:]


def human_filesize(nbytes: int) -> str:
    """
    Convert number of bytes to human-readable filesize string.
    Source: https://stackoverflow.com/questions/5194057/better-way-to-convert-file-sizes-in-python

    :param nbytes:number of bytes to format as string
    :type nbytes: int
    :return: string with human-readable filesize
    :rtype: str
    """

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    base = 1

    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']:
        n = nbytes / base

        if n < 9.95 and unit != 'B':
            # Less than 10 then keep 1 decimal place
            value = "{:.1f} {}".format(n, unit)
            return value

        if round(n) < 1000:
            # Less than 4 digits so use this
            value = "{} {}".format(round(n), unit)
            return value

        base *= 1024
    value = "{} {}".format(round(n), unit)

    return value


def split_at(lst, idx):
    """
    Split a list at a given index or list of indices.

    :param lst: list to split
    :type lst: list
    :param idx: indices to split the list at
    :type idx: list
    :return: list split at desired indices
    :rtype: list of lists
    """
    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())
    return [lst[i:j] for i, j in zip([0] + idx, idx + [None])]


def duplicated(lst):
    """
    Return list of boolean values indicating whether each item in a list
    is a duplicate of a previous item.

    :param lst: a list to test for duplicates
    :type lst: list
    :return: list of boolean values
    :rtype: list
    """

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

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


def make_md_list(string, li_type, tab_size=4):
    """
    Add markdown bullets to each element of markdown string, separated by \n.

    :param string: character string in markdown
    :type string: char
    :param li_type: type of list item, one of "1" (ordered list), or "-" or "*" (unordered list)
    :type li_type: char
    :param tab_size: size of whitespace indentation
    :type tab_size: int
    :return: markdown string with bullets
    :rtype: str
    """
    # FIXME: This should accept a list as a parameter, not a string delimited by \n or \\n

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    indent = ' ' * tab_size
    string = string.replace('\\t', indent).replace('\t', indent)

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
    Scan a given .md file `md_fpath` for headings denoted by "#". Then generate a table of
    contents based on the headings found in the file.

    :param md_fpath: path to Markdown file
    :type md_fpath: str
    :param li_type: type of list item, one of "1" (ordered list), or "-" or "*" (unordered list)
    :type li_type: str
    :return: markdown string
    :rtype: str
    """

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

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


def test(value, dtype, return_coerced_value=False, assertion=False):
    """
    Test if a value is an instance of type `dtype`. May accept a value of any kind.

    Parameter `dtype` must be one of ['bool', 'str', 'string', 'int', 'integer',
    'float', 'date', 'datetime', 'path', 'path exists'].

    Parameter `return_coerced_value` will return `value` as type `dtype` if possible, and will
    raise an error otherwise.

    Parameter `assertion` will cause this function to raise an error if `value` cannot be
    coerced to `dtype` instead of simply logging the error message.
    """
    import os
    import re
    from datetime import datetime
    from dateutil.parser import parse
    from dateutil.tz import tzoffset

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    class Attribute():
        pass

    def define_date_regex():
        """Define all date component regex strings."""
        rgx = Attribute()
        rgx.sep = r'(\.|\/|-|_|\:)'

        rgx.year = r'(?P<year>\d{4})'
        rgx.month = r'(?P<month>\d{2})'
        rgx.day = r'(?P<day>\d{2})'

        rgx.hour = r'(?P<hour>\d{2})'
        rgx.minute = r'(?P<minute>\d{2})'
        rgx.second = r'(?P<second>\d{2})'
        rgx.microsecond = r'(?P<microsecond>\d+)'

        rgx.tz_sign = r'(?P<tz_sign>-|\+)'
        rgx.tz_hour = r'(?P<tz_hour>\d{1,2})'
        rgx.tz_minute = r'(?P<tz_minute>\d{1,2})'

        rgx.date = '{rgx.year}{rgx.sep}{rgx.month}{rgx.sep}{rgx.day}'.format(**locals())
        rgx.datetime = r'{rgx.date} {rgx.hour}{rgx.sep}{rgx.minute}{rgx.sep}{rgx.second}'.format(**locals())
        rgx.datetime_timezone = r'{rgx.datetime}{rgx.tz_sign}{rgx.tz_hour}(:){rgx.tz_minute}'.format(**locals())
        rgx.datetime_microsecond = r'{rgx.datetime}(\.){rgx.microsecond}'.format(**locals())

        return rgx

    def anchor(x):
        return '^' + x + '$'

    valid_dtypes = ['bool',
                    'str', 'string',
                    'int', 'integer',
                    'float',
                    'date',
                    'datetime',
                    'path',
                    'path exists']
    assert dtype in valid_dtypes, "Datatype must be one of %s" % ', '.join(valid_dtypes)

    # Date/datetime regex definitions
    rgx = define_date_regex()

    coerced_value = None

    # Test bool
    if dtype == 'bool':
        if isinstance(value, bool):
            coerced_value = value
        else:
            if str(value).lower() in ['true', 't', 'yes', 'y']:
                coerced_value = True
            elif str(value).lower() in ['false', 'f', 'no', 'n']:
                coerced_value = False

    # Test string
    elif dtype in ['str', 'string']:
        try:
            coerced_value = str(value)
        except Exception as e:
            if assertion: raise e
            else: logger.info(str(e))

    # Test integer
    elif dtype in ['int', 'integer']:
        if isinstance(value, int):
            coerced_value = value
        elif str(value).isdigit():
            coerced_value = int(value)
        else:
            try:
                coerced_value = int(value)
            except Exception as e:
                if assertion: raise e
                else: logger.info(str(e))

    # Test float
    elif dtype == 'float':
        if isinstance(value, float) or isinstance(value, int):
            import pdb; pdb.set_trace()
            coerced_value = float(value)
        elif '.' in str(value):
            try:
                coerced_value = float(value)
            except Exception as e:
                if assertion: raise e
                else: logger.info(str(e))

    # Test date
    elif dtype == 'date':
        m = re.search(anchor(rgx.date), str(value).strip())
        if m:
            dt_components = dict(year=m.group('year'), month=m.group('month'), day=m.group('day'))
            dt_components = {k: int(v) for k, v in dt_components.items()}
            coerced_value = datetime(**dt_components)

    # Test datetime
    elif dtype == 'datetime':
        m_dt = re.search(anchor(rgx.datetime), str(value).strip())
        m_dt_tz = re.search(anchor(rgx.datetime_timezone), str(value).strip())
        m_dt_ms = re.search(anchor(rgx.datetime_microsecond), str(value).strip())

        if m_dt:
            dt_components = dict(year=m_dt.group('year'),
                                 month=m_dt.group('month'),
                                 day=m_dt.group('day'),
                                 hour=m_dt.group('hour'),
                                 minute=m_dt.group('minute'),
                                 second=m_dt.group('second'))
            dt_components = {k: int(v) for k, v in dt_components.items()}
            coerced_value = datetime(**dt_components)

        elif m_dt_tz:
            dt_components = dict(year=m_dt_tz.group('year'),
                                 month=m_dt_tz.group('month'),
                                 day=m_dt_tz.group('day'),
                                 hour=m_dt_tz.group('hour'),
                                 minute=m_dt_tz.group('minute'),
                                 second=m_dt_tz.group('second'))
            dt_components = {k: int(v) for k, v in dt_components.items()}

            second_offset = int(m_dt_tz.group('tz_hour'))*60*60
            second_offset = -second_offset if m_dt_tz.group('tz_sign') == '-' else second_offset

            dt_components['tzinfo'] = tzoffset(None, second_offset)
            coerced_value = datetime(**dt_components)

        elif m_dt_ms:
            dt_components = dict(year=m_dt_ms.group('year'),
                                 month=m_dt_ms.group('month'),
                                 day=m_dt_ms.group('day'),
                                 hour=m_dt_ms.group('hour'),
                                 minute=m_dt_ms.group('minute'),
                                 second=m_dt_ms.group('second'),
                                 microsecond=m_dt_ms.group('microsecond'))
            dt_components = {k: int(v) for k, v in dt_components.items()}
            coerced_value = datetime(**dt_components)

    # Test path
    elif dtype == 'path':
        if '/' in value or value == '.':
            coerced_value = value

    # Test path exists
    elif dtype == 'path exists':
        if os.path.isfile(value) or os.path.isdir(value):
            coerced_value = value

    # Close function
    if coerced_value is None:
        error_str = "Unable to coerce value '{}' (dtype: {}) to {}".format(
            str(value), type(value).__name__, dtype)
        logger.info(error_str)

        if return_coerced_value:
            raise ValueError(error_str)
        else:
            return False

    else:
        if return_coerced_value:
            return coerced_value
        else:
            return True


def get_input(msg='Enter input', mode='str', indicate_mode=False):
    """
    Get user input, optionally of specified format.

    :param msg: message to print to console
    :type msg: str
    :param mode: apply filter to user input, one of ['bool', 'date', 'int', 'float',
                 'str', 'file', 'filev', 'dir', 'dirv']. 'filev' and 'dirv'
                 options are 'file'/'dir' with an added layer of validation, to
    :type mode: strensure the file/dir exists
    :param indicate_mode: print type of anticipated datatype with message
    :type indicate_mode: bool
    :return: user input as string
    :rtype: str
    """
    import re
    import os

    assert mode in ['str', 'bool', 'date', 'int', 'float', 'file', 'filev', 'dir', 'dirv']

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    add_colon = lambda x: x + ': '
    add_clarification = lambda x, clar: x + ' ' + clar

    # Add suffix based on `mode`
    msg = re.sub(r': *$', '', msg).strip()
    if mode == 'bool':
        msg = add_clarification(msg, '(y/n)')
    elif mode == 'date':
        msg = add_clarification(msg, '(YYYY-MM-DD)')
    if indicate_mode:
        msg = add_clarification(msg, '{%s}' % mode)
    msg = add_colon(msg)

    uin_raw = input(msg)

    if mode == 'bool':
        while not pydoni.test(uin_raw, 'bool'):
            uin_raw = input("Must enter 'y' or 'n': ")
        if uin_raw.lower() in ['y', 'yes']:
            return True
        else:
            return False
    elif mode == 'date':
        while not pydoni.test(uin_raw, 'date') and uin_raw != '':
            uin_raw = input("Must enter valid date in format 'YYYY-MM-DD': ")
    elif mode == 'int':
        while not pydoni.test(uin_raw, 'int'):
            uin_raw = input('Must enter integer value: ')
        uin_raw = int(uin_raw)
    elif mode == 'float':
        while not pydoni.test(uin_raw, 'float'):
            uin_raw = input('Must enter float value: ')
    elif mode in ['file', 'filev', 'dir', 'dirv']:
        uin_raw = os.path.expanduser(uin_raw.strip())
        if mode == 'filev':
            while not os.path.isfile(uin_raw):
                uin_raw = input('Must enter existing file: ')
        elif mode == 'dirv':
            while not os.path.isdir(uin_raw):
                uin_raw = input('Must enter existing directory: ')

    return uin_raw


def get_input_inq(msg='Enter input', mode='str', indicate_mode=False):
    """
    Get user input for single line using PyInquirer module.

    :param msg: message to print to console
    :type msg: str
    :param mode: apply filter to user input, one of ['bool', 'date', 'int', 'float',
                 'str', 'file', 'filev', 'dir', 'dirv']. 'filev' and 'dirv' options
                 are 'file'/'dir' with an added layer of validation, to ensure the file/dir exists
    :type mode: str
    :param indicate_mode: print type of anticipated datatype with message
    :type indicate_mode: bool
    :return: user input as string
    :rtype: str
    """
    import re
    import os
    import PyInquirer as inq

    assert mode in ['str', 'bool', 'date', 'int', 'float', 'file', 'filev', 'dir', 'dirv']

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    def define_validator(mode):
        """
        Define 'InqValidator' class based on 'mode'.

            :param mode:'mode' parameter passed into parent
            :type mode: str

        :rtype: InqValidator
        """

        testfunc = lambda value: test(value, mode)

        class InqValidator(inq.Validator):
            def validate(self, document):
                if not testfunc(document.text):
                    raise inq.ValidationError(
                        message="Please enter a valid value of type '%s'" % mode,
                        cursor_position=len(document.text))

        return InqValidator

    add_colon = lambda x: x + ': '
    add_clarification = lambda x, clar: x + ' ' + clar

    # Add suffix based on `mode`
    msg = re.sub(r': *$', '', msg).strip()
    if mode == 'bool':
        msg = add_clarification(msg, '(y/n)')
    elif mode == 'date':
        msg = add_clarification(msg, '(YYYY-MM-DD)')
    if indicate_mode:
        msg = add_clarification(msg, '{%s}' % mode)

    msg = add_colon(msg)

    question = {
        'type': 'input',
        'name': 'TMP',
        'message': msg
    }

    if mode in ['bool', 'date', 'int', 'float', 'file', 'filev', 'dir', 'dirv']:
        validator = define_validator(mode)
        question['validate'] = validator

    question = [question]
    answer = inq.prompt(question)['TMP']

    if mode == 'int':
        answer = int(answer)
    elif mode == 'float':
        answer = float(answer)
    elif mode == 'bool':
        if answer.lower() in ['y', 'yes', 'true', 't']:
            answer = True
        elif answer.lower() in ['n', 'no', 'false', 'f']:
            answer = False
    elif mode in ['file', 'filev', 'dir', 'dirv']:
        answer = os.path.expanduser(answer)

    return answer


def continuous_prompt(msg, mode='str', indicate_mode=False, use_inq=False):
    """
    Continuously prompt the user for input until '' is entered.

    :param msg: message to print to console
    :type msg: str
    :param mode: apply filter to user input, one of ['bool', 'date', 'int', 'float',
                 'str', 'file', 'filev', 'dir', 'dirv']. 'filev' and 'dirv'
                 options are 'file'/'dir' with an added layer of validation, to
    :type mode: strensure the file/dir exists
    :param indicate_mode: print type of anticipated datatype with message
    :type indicate_mode: bool
    :param use_inq: use `pydoni.get_input_inq()` instead of `pydoni.get_input()`
    :return: user input as list
    :rtype: list
    """

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    uin = 'TMP'
    all_input = []

    while uin > '':
        if use_inq:
            uin = get_input_inq(msg=msg, mode=mode, indicate_mode=indicate_mode)
        else:
            uin = get_input(msg=msg, mode=mode, indicate_mode=indicate_mode)

        if uin > '':
            all_input.append(uin)

    return all_input


def extract_colorpalette(palette_name, n=None, mode='hex'):
    """
    Convert color palette to color ramp list.

    :param palette_name: name of color palette
    :type palette_name: str
    :param n: size of color ramp. If None, automatically return the maximum number of colors in the color palette
    :type n: int
    :param mode: type of colors to return, one of ['rgb', 'hex', 'ansi']
    :type mode: str
    :return: list of colors
    :rtype: list
    """
    import colr
    import itertools
    import matplotlib
    import numpy as np
    import pylab
    from collections import OrderedDict

    assert mode in ['rgb', 'hex', 'ansi']

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    if n is None:
        cmap_mpl = pylab.cm.get_cmap(palette_name)
    else:
        cmap_mpl = pylab.cm.get_cmap(palette_name, n)

    cmap = dict(rgb=OrderedDict(), hex=OrderedDict(), ansi=OrderedDict())
    for i in range(cmap_mpl.N):
        rgb = cmap_mpl(i)[:3]
        hex = matplotlib.colors.rgb2hex(rgb)
        ansi = colr.color('', fore=hex)
        cmap['rgb'].update({rgb: None})
        cmap['hex'].update({hex: None})
        cmap['ansi'].update({ansi: None})

    target = [x for x, _ in cmap[mode].items()]
    if n > len(target):
        rep = int(np.floor(n / len(target)))
        target = list(itertools.chain.from_iterable(itertools.repeat(x, rep) for x in target))
        target += [target[-1]] * (n - len(target))

    return target


def rename_dict_keys(d, key_dict):
    """
    Rename dictionary keys.

    :param d: dictionary to rename keys for
    :type d: dict
    :param key_dict: dict of k:v pairs where 'k' is current key name and 'v' is desired key name
    :type key_dict: dict
    :return: dictionary with renamed keys
    :rtype: dict
    """

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    for k, v in key_dict.items():
        if k in d.keys():
            d[v] = d.pop(k)

    return d


def append_filename_suffix(filename, suffix):
    """
    Add suffix string to filename before extension.

    :param filename: Name of file to append suffix to.
    :type filename: path exists
    :param suffix: Suffix string to append to filename.
    :type suffix: str
    """
    import os

    logger = pydoni.logger_setup(pydoni.what_is_my_name(), pydoni.modloglev)
    logger.logvars(locals())

    base, ext = os.path.splitext(filename)
    if ext == '.icloud':
        ext_icloud = ext
        base, ext = os.path.splitext(base)
        ext += ext_icloud

    return base + suffix + ext


def file_len(fname):
    """
    Get number of rows in a text file.
    Source: https://stackoverflow.com/questions/845058/how-to-get-line-count-of-a-large-file-cheaply-in-python
    """
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i + 1


def dirsize(start_path='.'):
    """
    Get size of directory in bytes.
    Source: https://stackoverflow.com/questions/1392413/calculating-a-directorys-size-using-python
    """
    import os

    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    return total_size


def pydonicli_register(var_dict):
    """
    Register variable as a part of the 'pydoni' module to be logged to the CLI's backend.
    """
    for key, value in var_dict.items():
        setattr(pydoni, 'pydonicli_' + key, value)


def pydonicli_declare_args(var_dict):
    """
    Filter `locals()` dictionary to only variables, and return empty dictionary for `result`.
    """
    vars_only = {}
    for k, v in var_dict.items():
        dtype = v.__class__.__name__
        if dtype not in ['module', 'function']:
            vars_only[k] = v

    return vars_only
