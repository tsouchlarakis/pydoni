def logger_setup(name, level='WARNING'):
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
