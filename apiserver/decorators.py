# encoding: utf-8

import types
from functools import wraps
from django.http import HttpResponse
from django.conf import settings

class on_view(object):
    def __init__(self, fn):
        self.wrapper = fn

    def decorate_fn(self, fn):
        return wraps(self.wrapper(fn))
        
    def decorate_cls(self, cls):    
        for name in cls.method_mapping.values():
            if hasattr(cls, name):
                method = getattr(cls, name)
                setattr(cls, name, self.decorate_fn(method))
        return cls

    def __call__(self, obj):
        if isinstance(obj, types.FunctionType):
            return self.decorate_fn(obj)
        else:
            return self.decorate_cls(obj)

canned_error = {
    "error": getattr(settings, "APISERVER_CANNED_ERROR", "Sorry, this request could not be processed. This is usually not your fault. Please try again later.")
    }

class on_error(on_view):
    """
    An error handling decorator. Usage:
    
    @on_error(NoObjectsFound, InvalidSortError, 404)
    @on_error(IOError, 503, custom_response)
    def my_view():
        raise IOError("Database down for maintenance")
    
    Works on Resource classes as well, in which case
    the class decorator will decorate the 'show', 'create', 
    'update' and 'destroy' methods.
    """
    
    def __init__(self, *vargs):
        vargs = list(vargs)
        if isinstance(vargs[-1], types.FunctionType):
            self.message = vargs.pop()
            self.status = vargs.pop()
        else:
            self.message = lambda *vargs, **kwargs: canned_error
            self.status = vargs.pop()
        
        self.exceptions = tuple(vargs)

    def decorate_fn(self, fn):
        @wraps(fn)
        def safe_fn(*vargs, **kwargs):
            try:
                return fn(*vargs, **kwargs)
            except self.exceptions:
                return self.message(*vargs, **kwargs), self.status
                
        return safe_fn

class only(on_view):
    """
    A shortcut decorator to only make certain methods available. Usage:
    
    @only("show", "create")
    class Person(api.ModelResource):
        ...
    """

    def __init__(self, *methods):
        self.methods = methods
    
    def decorate_fn(self, fn):
        if fn.__name__ in self.methods + ('options',):
            return fn
        else:
            def wrapped_fn(*vargs, **kwargs):
                raise NotImplementedError()
            wrapped_fn.not_implemented = True
            return wrapped_fn