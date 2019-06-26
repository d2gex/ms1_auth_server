import functools
from flask import request, current_app, redirect, url_for
from flask_login import current_user


def init_class(cls):
    '''Decorator that initialise a CLASS object after this has been created
    '''
    cls.init()
    return cls


def login_required(route, request_args=False, **additional_args):
    '''A decorator that works similarly to flask_login.login_required to allow custom target and query_string redirection.

    :param route: method of a particular view to be redirected to
    :param request_args: boolean flag that tells if all url parameters of request.args should be passed on
    :param additional_args: url arguments to be passed to the route
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if current_app.config.get('LOGIN_DISABLED'):
                return func(*args, **kwargs)
            if not current_user.is_authenticated:
                query_string = {key: value for key, value in request.args.items()} if request_args else {}
                query_string.update(additional_args)
                return redirect(url_for(route, **query_string))
            return func(*args, **kwargs)
        return wrapper
    return decorator
