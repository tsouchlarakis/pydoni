import inspect
import sys

modloglev = 'INFO'


def what_is_my_name(with_modname=True):
    """
    Return name of function that calls this function.

    :param with_modname {bool} -- append module name to beginning of function name (True)
    :return: {str}
    """
    work = inspect.stack()[1][3]

    if with_modname:
        frm = inspect.stack()[1]
        mod = inspect.getmodule(frm[0])
        work = '.'.join([mod.__name__, work])
    
    return work

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
