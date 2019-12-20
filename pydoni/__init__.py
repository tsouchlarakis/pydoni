import inspect
import sys

modloglev = 'INFO'


def what_is_my_name(classname=None, with_modname=True):
    """
    Return name of function that calls this function. If called from a
    classmethod, include classname before classmethod in output string.

    :param with_modname {bool} -- append module name to beginning of function name (True)
    :return: {str}
    """
    lst = []
    funcname = inspect.stack()[1][3]

    if with_modname:
        modulename = inspect.getmodule(inspect.stack()[1][0]).__name__
        lst += [modulename]

    if isinstance(classname, str):
        lst += [classname]

    lst += [funcname]
    return '.'.join(lst)

def logger_setup(name, level=modloglev):
    """
    Define an identical logger object for all pydoni submodules.

    :param level {str}: desired logging.Logger level
    """
    import logging
    
    logger = logging.getLogger(name)
    logger_fmt = '%(asctime)s : %(levelname)s : %(name)s : %(message)s'
    
    formatter = logging.Formatter(logger_fmt)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, level))

    return logger
