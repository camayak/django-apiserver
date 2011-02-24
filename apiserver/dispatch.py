# encoding: utf-8

# TODO: this is Flask code, I've yet to port this to Django -- but the basic 
# way of doing things can remain intact.

from django.http import HttpResponse
import types
from functools import wraps
import utils

MIMETYPES = {
    'json': 'application/json',
    'xml':  'text/xml',
    'txt': 'text/plain',
    'yaml': 'text/yaml',
    'html': 'text/html',
    'atom': 'application/atom+xml',
    }

"""
This code is a bit cryptic by itself. See :func:`formatted_response` in serializers.py
and the initialization routine of the RESTController (controllers.py) to get a better 
grasp of how this fits into the code flow.

In a nutshell, it works like this: 
1. we define a view (e.g. the method `show` on a RESTController subclass)
2. we render the view by passing a python object to formatted_response
3. formatted_response returns a dictionary of possible formats, and the functions
   that render each specific format (using serializers)
4. format_dispatcher, which wraps our view, inspecting the request, decides
   which format the user wishes for, selects it from the dictionary returned by
   formatted_response, executes it, sets the appropriate mimetype and then returns
   the response.
"""

def format_dispatcher(app, view):
    @utils.timed()
    def format_aware_view(request, **kwargs):
        format = kwargs['format']
        request.format = format
        del kwargs['format']
        initialized_view = view(request, **kwargs)
        if format not in initialized_view:
            # not implemented
            return HttpResponse(status=501)
        rendered_view = initialized_view[format]()
        response = app.make_response(rendered_view)
        response.mimetype = MIMETYPES[format]
        return response
    return format_aware_view