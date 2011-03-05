# encoding: utf-8

import logging
import dispatch
import inspect
import utils
import serializers
from surlex import surlex_to_regex
from surlex.grammar import Parser, TextNode, BlockNode
from django.conf.urls.defaults import patterns, url
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from apiserver.bundle import Bundle
from tastypie import resources as tastypie

log = logging.getLogger("apiserver")

class re(str):
    pass

def get_format(request, kwargs):
    format = "json"
    if 'format' in kwargs:
        format = kwargs['format']
    

# a Railsy REST resource
class Resource(object):
    serializer = serializers.Serializer()

    @property
    def methods(self):
        return {
            'GET': self.show,
            'POST': self.create,
            'PUT': self.update,
            'DELETE': self.destroy,        
            'OPTIONS': self.options, 
            'PATCH': self.patch,   
            }
        
    def show(self, request, **kwargs):
        pass
    
    def create(self, request, **kwargs):
        pass

    def update(self, request, **kwargs):
        pass

    def destroy(self, request, **kwargs):
        pass

    def options(self, request, **kwargs):
        pass
        
    def patch(self, request, **kwargs):
        pass

    def serialize(self, request, data, format, options=None):
        """
        Given a request, data and a desired format, produces a serialized
        version suitable for transfer over the wire.
        
        Mostly a hook, this uses the ``Serializer`` from ``Resource._meta``.
        """
        options = options or {}
        
        if 'text/javascript' in format:
            # get JSONP callback name. default to "callback"
            callback = request.GET.get('callback', 'callback')
            
            if not is_valid_jsonp_callback_value(callback):
                raise BadRequest('JSONP callback name is invalid.')
            
            options['callback'] = callback
        
        return self.serializer.serialize(data, format, options)
    
    def deserialize(self, request, data, format='application/json'):
        """
        Given a request, data and a format, deserializes the given data.
        
        It relies on the request properly sending a ``CONTENT_TYPE`` header,
        falling back to ``application/json`` if not provided.
        
        Mostly a hook, this uses the ``Serializer`` from ``Resource._meta``.
        """
        return self.serializer.deserialize(data, format=request.META.get('CONTENT_TYPE', 'application/json'))

    def build_bundle(self, obj=None, data=None):
        """
        Given either an object, a data dictionary or both, builds a ``Bundle``
        for use throughout the ``dehydrate/hydrate`` cycle.
        
        If no object is provided, an empty object from
        ``Resource._meta.object_class`` is created so that attempts to access
        ``bundle.obj`` do not fail.
        """
        if obj is None:
            obj = self._meta.object_class()
        
        return Bundle(obj, data)

    def dispatch(self, request, **kwargs):            
        view = self.methods[request.method]
        
        format = utils.mime.determine_format(request, kwargs['format'], self.serializer)
        
        raw_response = view(request, **kwargs)
        return HttpResponse(self.serialize(request, raw_response, format))

    def __init__(self):
        if not isinstance(self.route, re):
            self.route = surlex_to_regex(self.route)
        self.route = self.route.rstrip('/') + '(\.(?P<format>[\w]+))?$'

        for method in self.methods:
            name = self.__class__.__name__ + '#' + self.methods[method].__name__
            route_with_method = '{0} {1}'.format(method, self.route)
            log.info('Registered {0} for {1}'.format(route_with_method, name))


def get_attribute(obj, attr_string):
    attrs = attr_string.split("__")
    for attr in attrs:
        obj = getattr(obj, attr) 
    return obj

class ModelResource(Resource):
    # not strictly correct, a first stab
    def get_resource_uri(self, obj):
        nodes = Parser(self.__class__.route).get_node_list()
        print nodes
        uri = ''
        for node in nodes:
            print uri
            if isinstance(node, TextNode):
                uri += node.token
            else:
                uri += str(get_attribute(obj, node.name))
        
        return uri

    def get_object_list(self, request):
        """
        An ORM-specific implementation of ``get_object_list``.
        
        Returns a queryset that may have been limited by authorization or other
        overrides.
        """
        base_object_list = self.queryset
        return base_object_list
        
        # Limit it as needed.
        authed_object_list = self.apply_authorization_limits(request, base_object_list)
        return authed_object_list

    def obj_get_list(self, request=None, **kwargs):       
        try:
            return self.get_object_list(request).filter(**kwargs)
        except ValueError, e:
            raise NotFound("Invalid resource lookup data provided (mismatched type).")
    
    def obj_get(self, request=None, **kwargs):
        """
        A ORM-specific implementation of ``obj_get``.
        
        Takes optional ``kwargs``, which are used to narrow the query to find
        the instance.
        """
        try:
            return self.obj_get_list(request).get(**kwargs)
        except ValueError, e:
            raise NotFound("Invalid resource lookup data provided (mismatched type).")
    
    def show(self, request, **kwargs):
        """
        Returns a single serialized resource.
        
        Calls ``cached_obj_get/obj_get`` to provide the data, then handles that result
        set and serializes it.
        
        Should return a HttpResponse (200 OK).
        """
        del kwargs['format']
        try:
            obj = self.obj_get(request, **kwargs)
        except ObjectDoesNotExist:
            return None

        return obj.__dict__


class CollectionResource(ModelResource):
    def show(self, request, **kwargs):
        del kwargs['format']
        objs = self.obj_get_list(request, **kwargs)
        return [obj.__dict__ for obj in objs]