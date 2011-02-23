from django.http import HttpResponse


class TastypieError(Exception):
    """A base exception for other tastypie-related errors."""
    pass


class HydrationError(TastypieError):
    """Raised when there is an error hydrating data."""
    pass


class NotRegistered(TastypieError):
    """
    Raised when the requested resource isn't registered with the ``Api`` class.
    """
    pass


class NotFound(TastypieError):
    """
    Raised when the resource/object in question can't be found.
    """
    pass


class ApiFieldError(TastypieError):
    """
    Raised when there is a configuration error with a ``ApiField``.
    """
    pass


class UnsupportedFormat(TastypieError):
    """
    Raised when an unsupported serialization format is requested.
    """
    pass


class BadRequest(TastypieError):
    """
    A generalized exception for indicating incorrect request parameters.
    
    Handled specially in that the message tossed by this exception will be
    presented to the end user.
    """
    pass


class BlueberryFillingFound(TastypieError):
    pass


class InvalidFilterError(TastypieError):
    """
    Raised when the end user attempts to use a filter that has not be
    explicitly allowed.
    """
    pass


class InvalidSortError(TastypieError):
    """
    Raised when the end user attempts to sort on a field that has not be
    explicitly allowed.
    """
    pass


class ImmediateHttpResponse(TastypieError):
    """
    This exception is used to interrupt the flow of processing to immediately
    return a custom HttpResponse.
    
    Common uses include::
    
        * for authentication (like digest/OAuth)
        * for throttling
    
    """
    response = HttpResponse("Nothing provided.")
    
    def __init__(self, response):
        self.response = response


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