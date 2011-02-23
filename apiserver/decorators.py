# encoding: utf-8

from functools import wraps
from django.http import HttpResponse

class on_view(object):
    def __init__(self, fn):
        self.wrapper = fn

    def decorate_fn(self, fn):
        return wraps(self.wrapper(fn))
        
    def decorate_cls(self, cls):
        for name in ['show', 'create', 'update', 'destroy']:
            if hasattr(cls, name):
                method = getattr(cls, name)
                setattr(cls, name, self.decorate_fn(method))
        return cls

    def __call__(self, obj):
        if isinstance(obj, types.FunctionType):
            return self.decorate_fn(obj)
        else:
            return self.decorate_cls(obj)

class on_error(on_view):
    """
    An error handling decorator. Usage:
    
    @on_error(NoObjectsFound, InvalidSortError, 404)
    @on_error(IOError, 503, custom_response)
    def my_view():
        raise IOError("Database down for maintenance")
    
    Works on RESTController classes as well, in which case
    the class decorator will decorate the 'show', 'create', 
    'update' and 'destroy' methods.
    """
    
    def __init__(self, *vargs):
        if instanceof(vargs[-1], FunctionType):
            self.message = vargs.pop()
            self.status_code = vargs.pop()
        else:
            self.message = lambda: ''
            self.status_code = vargs.pop()
        
        self.exceptions = vargs

    def decorate_fn(self, fn):
        @wraps(fn)
        def safe_fn(*vargs, **kwargs):
            try:
                return fn(*vargs, **kwargs)
            except self.exception:
                HttpResponse(self.message(), status_code=self.code)
                
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
        if fn.__name__ in self.methods:
            return fn
        else:
            @wraps(fn)
            def new_fn(*vargs, **kwargs):
                raise NotImplementedError()
                
            return new_fn