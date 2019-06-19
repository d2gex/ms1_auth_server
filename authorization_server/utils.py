def init_class(cls):
    '''Decorator that initialise a CLASS object after this has been created
    '''
    cls.init()
    return cls
