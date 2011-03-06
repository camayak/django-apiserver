# encoding: utf-8

import logging
import inspect

from django.conf.urls.defaults import patterns, url
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse

from surlex import surlex_to_regex
from surlex.grammar import Parser, TextNode, BlockNode

from tastypie import resources as tastypie

from apiserver.bundle import Bundle
from apiserver.fields import *
from apiserver import serializers
from apiserver import utils
from apiserver import dispatch
from apiserver.options import ResourceOptions

log = logging.getLogger("apiserver")

class re(str):
    pass


class DeclarativeMetaclass(type):
    def __new__(cls, name, bases, attrs):
        attrs['base_fields'] = {}
        declared_fields = {}
        
        # Inherit any fields from parent(s).
        try:
            parents = [b for b in bases if issubclass(b, Resource)]
            
            for p in parents:
                fields = getattr(p, 'base_fields', {})
                
                for field_name, field_object in fields.items():
                    attrs['base_fields'][field_name] = deepcopy(field_object)
        except NameError:
            pass
        
        for field_name, obj in attrs.items():
            if isinstance(obj, ApiField):
                field = attrs.pop(field_name)
                declared_fields[field_name] = field
        
        attrs['base_fields'].update(declared_fields)
        attrs['declared_fields'] = declared_fields
        new_class = super(DeclarativeMetaclass, cls).__new__(cls, name, bases, attrs)
        opts = getattr(new_class, 'Meta', None)
        new_class._meta = ResourceOptions(opts)
        
        if not getattr(new_class._meta, 'resource_name', None):
            # No ``resource_name`` provided. Attempt to auto-name the resource.
            class_name = new_class.__name__
            name_bits = [bit for bit in class_name.split('Resource') if bit]
            resource_name = ''.join(name_bits).lower()
            new_class._meta.resource_name = resource_name
        
        if getattr(new_class._meta, 'include_resource_uri', True):
            if not 'resource_uri' in new_class.base_fields:
                new_class.base_fields['resource_uri'] = CharField(readonly=True)
        elif 'resource_uri' in new_class.base_fields and not 'resource_uri' in attrs:
            del(new_class.base_fields['resource_uri'])
        
        for field_name, field_object in new_class.base_fields.items():
            if hasattr(field_object, 'contribute_to_class'):
                field_object.contribute_to_class(new_class, field_name)
        
        return new_class


# a Railsy REST resource
class Resource(object):
    """
    Handles the data, request dispatch and responding to requests.
    
    Serialization/deserialization is handled "at the edges" (i.e. at the
    beginning/end of the request/response cycle) so that everything internally
    is Python data structures.
    
    This class tries to be non-model specific, so it can be hooked up to other
    data sources, such as search results, files, other data, etc.
    """
    __metaclass__ = DeclarativeMetaclass

    serializer = serializers.Serializer()

    @property
    def name(self):
        path = self.__class__.__module__ + '.' + self.__class__.__name__
        # with dots, Django would interpret this as a reference
        # to an actual view function, which it isn't
        return path.replace(".", "-")

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
        
    def show(self, request, filters, format):
        pass
    
    def create(self, request, filters, format):
        pass

    def update(self, request, filters, format):
        pass

    def destroy(self, request, filters, format):
        pass

    def options(self, request, filters, format):
        pass
        
    def patch(self, request, filters, format):
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
        raw_format = kwargs['format']
        del kwargs['format']
        format = utils.mime.determine_format(request, raw_format, self._meta.serializer)
        raw_response = view(request, kwargs, raw_format)
        return HttpResponse(self.serialize(request, raw_response, format))

    def __init__(self):
        route = self._meta.route
        if not isinstance(route, re):
            route = surlex_to_regex(route)
        route = route.rstrip('/') + '(\.(?P<format>[\w]+))?$'
        self._meta.parsed_route = route

        methods = ", ".join(self.methods.keys())
        route_with_method = '{0} {1}'.format(methods, self._meta.route)
        log.info('Registered ' + route_with_method)


class ModelDeclarativeMetaclass(DeclarativeMetaclass):
    def __new__(cls, name, bases, attrs):
        meta = attrs.get('Meta')
                
        if meta and hasattr(meta, 'queryset'):
            setattr(meta, 'object_class', meta.queryset.model)
        
        new_class = super(ModelDeclarativeMetaclass, cls).__new__(cls, name, bases, attrs)
        fields = getattr(new_class._meta, 'fields', [])
        excludes = getattr(new_class._meta, 'excludes', [])
        field_names = new_class.base_fields.keys()
        
        for field_name in field_names:
            if field_name == 'resource_uri':
                continue
            if field_name in new_class.declared_fields:
                continue
            if len(fields) and not field_name in fields:
                del(new_class.base_fields[field_name])
            if len(excludes) and field_name in excludes:
                del(new_class.base_fields[field_name])
        
        # Add in the new fields.
        new_class.base_fields.update(new_class.get_fields(fields, excludes))
        
        if getattr(new_class._meta, 'include_absolute_url', True):
            if not 'absolute_url' in new_class.base_fields:
                new_class.base_fields['absolute_url'] = CharField(attribute='get_absolute_url', readonly=True)
        elif 'absolute_url' in new_class.base_fields and not 'absolute_url' in attrs:
            del(new_class.base_fields['absolute_url'])
        
        return new_class


class ModelResource(Resource):
    __metaclass__ = ModelDeclarativeMetaclass

    @classmethod
    def should_skip_field(cls, field):
        """
        Given a Django model field, return if it should be included in the
        contributed ApiFields.
        """
        # Ignore certain fields (related fields).
        if getattr(field, 'rel'):
            return True
        
        return False
    
    @classmethod
    def api_field_from_django_field(cls, f, default=CharField):
        """
        Returns the field type that would likely be associated with each
        Django type.
        """
        result = default
        
        if f.get_internal_type() in ('DateField', 'DateTimeField'):
            result = DateTimeField
        elif f.get_internal_type() in ('BooleanField', 'NullBooleanField'):
            result = BooleanField
        elif f.get_internal_type() in ('DecimalField', 'FloatField'):
            result = FloatField
        elif f.get_internal_type() in ('IntegerField', 'PositiveIntegerField', 'PositiveSmallIntegerField', 'SmallIntegerField'):
            result = IntegerField
        elif f.get_internal_type() in ('FileField', 'ImageField'):
            result = FileField
        # TODO: Perhaps enable these via introspection. The reason they're not enabled
        #       by default is the very different ``__init__`` they have over
        #       the other fields.
        # elif f.get_internal_type() == 'ForeignKey':
        #     result = ForeignKey
        # elif f.get_internal_type() == 'ManyToManyField':
        #     result = ManyToManyField
    
        return result
    
    @classmethod
    def get_fields(cls, fields=None, excludes=None):
        """
        Given any explicit fields to include and fields to exclude, add
        additional fields based on the associated model.
        """
        final_fields = {}
        fields = fields or []
        excludes = excludes or []
        
        if not cls._meta.object_class:
            return final_fields
        
        for f in cls._meta.object_class._meta.fields:
            # If the field name is already present, skip
            if f.name in cls.base_fields:
                continue
            
            # If field is not present in explicit field listing, skip
            if fields and f.name not in fields:
                continue
            
            # If field is in exclude list, skip
            if excludes and f.name in excludes:
                continue
            
            if cls.should_skip_field(f):
                continue
            
            api_field_class = cls.api_field_from_django_field(f)
            
            kwargs = {
                'attribute': f.name,
                'help_text': f.help_text,
            }
            
            if f.null is True:
                kwargs['null'] = True

            kwargs['unique'] = f.unique
            
            if not f.null and f.blank is True:
                kwargs['default'] = ''
            
            if f.get_internal_type() == 'TextField':
                kwargs['default'] = ''
            
            if f.has_default():
                kwargs['default'] = f.default
            
            final_fields[f.name] = api_field_class(**kwargs)
            final_fields[f.name].instance_name = f.name
        
        return final_fields

    # not strictly correct, a first stab
    def get_resource_uri(self, obj):
        filters = {}
        nodes = Parser(self.__class__._meta.route).get_node_list()        
        for node in nodes:
            if not isinstance(node, TextNode):
                filters[node.name] = str(utils.traverse(obj, node.name))        
        
        return reverse(self.name, kwargs=filters)

    def get_object_list(self, request):
        """
        An ORM-specific implementation of ``get_object_list``.
        
        Returns a queryset that may have been limited by authorization or other
        overrides.
        """
        base_object_list = self._meta.queryset
        return base_object_list
        
        # Limit it as needed.
        #authed_object_list = self.apply_authorization_limits(request, base_object_list)
        #return authed_object_list

    def obj_get_list(self, request=None, filters={}):       
        try:
            return self.get_object_list(request).filter(**filters)
        except ValueError, e:
            raise NotFound("Invalid resource lookup data provided (mismatched type).")
    
    def obj_get(self, request=None, filters={}):
        """
        A ORM-specific implementation of ``obj_get``.
        
        Takes optional ``kwargs``, which are used to narrow the query to find
        the instance.
        """
        try:
            return self.obj_get_list(request).get(**filters)
        except ValueError, e:
            raise NotFound("Invalid resource lookup data provided (mismatched type).")
    
    def show(self, request, filters, format):
        """
        Returns a single serialized resource.
        
        Calls ``cached_obj_get/obj_get`` to provide the data, then handles that result
        set and serializes it.
        
        Should return a HttpResponse (200 OK).
        """
        try:
            obj = self.obj_get(request, filters)
        except ObjectDoesNotExist:
            return None

        return obj.__dict__


class CollectionResource(ModelResource):
    def show(self, request, filters, format):
        objs = self.obj_get_list(request, filters)
        return [obj.__dict__ for obj in objs]