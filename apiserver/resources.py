# encoding: utf-8

import logging
import inspect
import re

from django.conf.urls.defaults import patterns, url
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse, NoReverseMatch

from surlex import surlex_to_regex

from tastypie import resources as tastypie
from apiserver import bundle, dispatch, serializers, utils, options
from apiserver.paginator import Paginator
from apiserver.fields import *

try:
    set
except NameError:
    from sets import Set as set
# The ``copy`` module was added in Python 2.5 and ``copycompat`` was added in
# post 1.1.1 Django (r11901)
try:
    from django.utils.copycompat import deepcopy
    from django.views.decorators.csrf import csrf_exempt
except ImportError:
    from copy import deepcopy
    def csrf_exempt(func):
        return func

log = logging.getLogger("apiserver")

class r(str):
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
        new_class._meta = options.ResourceOptions(opts)
        
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


# a Railsy RESTful resource
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

    def _parse_route(self):
        route = self._meta.route
        if not route:
            self._meta.parsed_route = False
            return

        if not isinstance(route, r):
            route = surlex_to_regex(route)
        route = route.rstrip('/') + '(\.(?P<__format>[\w]+))?$'
        self._meta.parsed_route = route

        methods = ", ".join(self.methods.keys())
        route_with_method = '{0} {1}'.format(methods, self._meta.route)
        log.info('Registered ' + route_with_method)    

    def __init__(self):
        self._parse_route()
        self.fields = deepcopy(self.base_fields)
    
    def __getattr__(self, name):
        if name in self.fields:
            return self.fields[name]
        raise AttributeError

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
  
    # not decided yet on whether to do this like Tastypie or differently
    def wrap_view(self, view):
        """
        Wraps methods so they can be called in a more functional way as well
        as handling exceptions better.
        
        Note that if ``BadRequest`` or an exception with a ``response`` attr
        are seen, there is special handling to either present a message back
        to the user or return the response traveling with the exception.
        """
        raise NotImplementedError()

    # not decided yet on whether to do this like Tastypie or differently
    def _handle_500(self, request, exception):
        raise NotImplementedError()

    def determine_format(self, request, raw_format):
        """
        Used to determine the desired format.
        
        Largely relies on ``tastypie.utils.mime.determine_format`` but here
        as a point of extension.
        """
        return utils.determine_format(request, raw_format, self._meta.serializer)

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
        
        return self._meta.serializer.serialize(data, format, options)
    
    def deserialize(self, request, data, format='application/json'):
        """
        Given a request, data and a format, deserializes the given data.
        
        It relies on the request properly sending a ``CONTENT_TYPE`` header,
        falling back to ``application/json`` if not provided.
        
        Mostly a hook, this uses the ``Serializer`` from ``Resource._meta``.
        """
        return self._meta.serializer.deserialize(data, format=request.META.get('CONTENT_TYPE', 'application/json'))

    def dispatch(self, request, **kwargs):            
        """
        Handles the common operations (allowed HTTP method, authentication,
        throttling, method lookup) surrounding most CRUD interactions.
        """
        view = self.methods[request.method]
        raw_format, kwargs = utils.extract('__format', kwargs)
        raw_response = view(request, kwargs, raw_format)
        format = self.determine_format(request, raw_format)
        return HttpResponse(self.serialize(request, raw_response, format))

        """
        allowed_methods = getattr(self._meta, "%s_allowed_methods" % request_type, None)
        request_method = self.method_check(request, allowed=allowed_methods)
        
        method = getattr(self, "%s_%s" % (request_method, request_type), None)
        
        if method is None:
            raise ImmediateHttpResponse(response=HttpNotImplemented())
        
        self.is_authenticated(request)
        self.is_authorized(request)
        self.throttle_check(request)
        
        # All clear. Process the request.
        request = convert_post_to_put(request)
        response = method(request, **kwargs)
        
        # Add the throttled request.
        self.log_throttled_access(request)
        
        # If what comes back isn't a ``HttpResponse``, assume that the
        # request was accepted and that some action occurred. This also
        # prevents Django from freaking out.
        if not isinstance(response, HttpResponse):
            return HttpAccepted()
        
        return response
        """

    def method_check(self, request, allowed=None):
        """
        Ensures that the HTTP method used on the request is allowed to be
        handled by the resource.
        
        Takes an ``allowed`` parameter, which should be a list of lowercase
        HTTP methods to check against. Usually, this looks like::
        
            # The most generic lookup.
            self.method_check(request, self._meta.allowed_methods)
            
            # A lookup against what's allowed for list-type methods.
            self.method_check(request, self._meta.list_allowed_methods)
            
            # A useful check when creating a new endpoint that only handles
            # GET.
            self.method_check(request, ['get'])
        """
        raise NotImplementedError()

    def is_authorized(self, request, object=None):
        """
        Handles checking of permissions to see if the user has authorization
        to GET, POST, PUT, or DELETE this resource.  If ``object`` is provided,
        the authorization backend can apply additional row-level permissions
        checking.
        """
        auth_result = self._meta.authorization.is_authorized(request, object)

        if isinstance(auth_result, HttpResponse):
            raise ImmediateHttpResponse(response=auth_result)
        
        if not auth_result is True:
            raise ImmediateHttpResponse(response=HttpUnauthorized())
    
    def is_authenticated(self, request):
        """
        Handles checking if the user is authenticated and dealing with
        unauthenticated users.
        
        Mostly a hook, this uses class assigned to ``authentication`` from
        ``Resource._meta``.
        """
        # Authenticate the request as needed.
        auth_result = self._meta.authentication.is_authenticated(request)
        
        if isinstance(auth_result, HttpResponse):
            raise ImmediateHttpResponse(response=auth_result)
        
        if not auth_result is True:
            raise ImmediateHttpResponse(response=HttpUnauthorized())

    def throttle_check(self, request):
        """
        Handles checking if the user should be throttled.
        
        Mostly a hook, this uses class assigned to ``throttle`` from
        ``Resource._meta``.
        """
        identifier = self._meta.authentication.get_identifier(request)
        
        # Check to see if they should be throttled.
        if self._meta.throttle.should_be_throttled(identifier):
            # Throttle limit exceeded.
            raise ImmediateHttpResponse(response=HttpForbidden())
    
    def log_throttled_access(self, request):
        """
        Handles the recording of the user's access for throttling purposes.
        
        Mostly a hook, this uses class assigned to ``throttle`` from
        ``Resource._meta``.
        """
        request_method = request.method.lower()
        self._meta.throttle.accessed(self._meta.authentication.get_identifier(request), url=request.get_full_path(), request_method=request_method)

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
        
        return bundle.Bundle(obj, data)

    # I'd prefer to do this using Alex Gaynor's django-filter
    def build_filters(self, filters=None):
        """
        Allows for the filtering of applicable objects.
        
        This needs to be implemented at the user level.'
        
        ``ModelResource`` includes a full working version specific to Django's
        ``Models``.
        """
        return filters

    def apply_sorting(self, obj_list, options=None):
        """
        Allows for the sorting of objects being returned.
        
        This needs to be implemented at the user level.
        
        ``ModelResource`` includes a full working version specific to Django's
        ``Models``.
        """
        return obj_list

    def get_resource_uri(self, bundle_or_obj):
        """
        This needs to be implemented at the user level.
        
        A ``return reverse("api_dispatch_detail", kwargs={'resource_name':
        self.resource_name, 'pk': object.id})`` should be all that would
        be needed.
        
        ``ModelResource`` includes a full working version specific to Django's
        ``Models``.
        """
        raise NotImplementedError()

    # TODO
    def get_resource_list_uri(self):
        return ''

    # NEEDS WORK (c&p from tastypie)
    def get_via_uri(self, uri):
        """
        This pulls apart the salient bits of the URI and populates the
        resource via a ``obj_get``.
        
        If you need custom behavior based on other portions of the URI,
        simply override this method.
        """
        try:
            view, args, kwargs = resolve(uri)
        except Resolver404:
            raise NotFound("The URL provided '%s' was not a link to a valid resource." % uri)
        
        return self.obj_get(**self.remove_api_resource_names(kwargs))

    # Data preparation.
    
    def full_dehydrate(self, obj):
        """
        Given an object instance, extract the information from it to populate
        the resource.
        """
        bundle = Bundle(obj=obj)
        
        # Dehydrate each field.
        for field_name, field_object in self.fields.items():
            # A touch leaky but it makes URI resolution work.
            if isinstance(field_object, RelatedField):
                field_object.api_name = self._meta.api_name
                field_object.resource_name = self._meta.resource_name
                
            bundle.data[field_name] = field_object.dehydrate(bundle)
            
            # Check for an optional method to do further dehydration.
            method = getattr(self, "dehydrate_%s" % field_name, None)
            
            if method:
                bundle.data[field_name] = method(bundle)
        
        bundle = self.dehydrate(bundle)
        return bundle
    
    def dehydrate(self, bundle):
        """
        A hook to allow a final manipulation of data once all fields/methods
        have built out the dehydrated data.
        
        Useful if you need to access more than one dehydrated field or want
        to annotate on additional data.
        
        Must return the modified bundle.
        """
        return bundle
    
    def full_hydrate(self, bundle):
        """
        Given a populated bundle, distill it and turn it back into
        a full-fledged object instance.
        """
        if bundle.obj is None:
            bundle.obj = self._meta.object_class()
        
        for field_name, field_object in self.fields.items():
            if field_object.attribute:
                value = field_object.hydrate(bundle)
                
                if value is not None:
                    # We need to avoid populating M2M data here as that will
                    # cause things to blow up.
                    if not getattr(field_object, 'is_related', False):
                        setattr(bundle.obj, field_object.attribute, value)
                    elif not getattr(field_object, 'is_m2m', False):
                        setattr(bundle.obj, field_object.attribute, value.obj)
            
            # Check for an optional method to do further hydration.
            method = getattr(self, "hydrate_%s" % field_name, None)
            
            if method:
                bundle = method(bundle)
        
        bundle = self.hydrate(bundle)
        return bundle
    
    def hydrate(self, bundle):
        """
        A hook to allow a final manipulation of data once all fields/methods
        have built out the hydrated data.
        
        Useful if you need to access more than one hydrated field or want
        to annotate on additional data.
        
        Must return the modified bundle.
        """
        return bundle
    
    def hydrate_m2m(self, bundle):
        """
        Populate the ManyToMany data on the instance.
        """
        if bundle.obj is None:
            raise HydrationError("You must call 'full_hydrate' before attempting to run 'hydrate_m2m' on %r." % self)
        
        for field_name, field_object in self.fields.items():
            if not getattr(field_object, 'is_m2m', False):
                continue
            
            if field_object.attribute:
                # Note that we only hydrate the data, leaving the instance
                # unmodified. It's up to the user's code to handle this.
                # The ``ModelResource`` provides a working baseline
                # in this regard.
                bundle.data[field_name] = field_object.hydrate_m2m(bundle)
        
        for field_name, field_object in self.fields.items():
            if not getattr(field_object, 'is_m2m', False):
                continue
            
            method = getattr(self, "hydrate_%s" % field_name, None)
            
            if method:
                method(bundle)
        
        return bundle

    def dehydrate_resource_uri(self, bundle):
        """
        For the automatically included ``resource_uri`` field, dehydrate
        the URI for the given bundle.
        
        Returns empty string if no URI can be generated.
        """
        try:
            return self.get_resource_uri(bundle)
        except NotImplementedError:
            return ''
        except NoReverseMatch:
            return ''
    
    def generate_cache_key(self, *args, **kwargs):
        """
        Creates a unique-enough cache key.
        
        This is based off the current api_name/resource_name/args/kwargs.
        """
        smooshed = []
        
        for key, value in kwargs.items():
            smooshed.append("%s=%s" % (key, value))
        
        # Use a list plus a ``.join()`` because it's faster than concatenation.
        return "%s:%s:%s:%s" % (self._meta.api_name, self._meta.resource_name, ':'.join(args), ':'.join(smooshed))

    # Data access methods.
    
    def get_object_list(self, request):
        """
        A hook to allow making returning the list of available objects.
        
        This needs to be implemented at the user level.
        
        ``ModelResource`` includes a full working version specific to Django's
        ``Models``.
        """
        raise NotImplementedError()
    
    def apply_authorization_limits(self, request, object_list):
        """
        Allows the ``Authorization`` class to further limit the object list.
        Also a hook to customize per ``Resource``.
        """
        if hasattr(self._meta.authorization, 'apply_limits'):
            object_list = self._meta.authorization.apply_limits(request, object_list)
        
        return object_list
    
    def obj_get_list(self, request=None, filters={}):
        """
        Fetches the list of objects available on the resource.
        
        This needs to be implemented at the user level.
        
        ``ModelResource`` includes a full working version specific to Django's
        ``Models``.
        """
        raise NotImplementedError()
    
    def cached_obj_get_list(self, request=None, filters={}):
        """
        A version of ``obj_get_list`` that uses the cache as a means to get
        commonly-accessed data faster.
        """
        cache_key = self.generate_cache_key('list', filters)
        obj_list = self._meta.cache.get(cache_key)
        
        if obj_list is None:
            obj_list = self.obj_get_list(request, filters)
            self._meta.cache.set(cache_key, obj_list)
        
        return obj_list
    
    def obj_get(self, request=None, **kwargs):
        """
        Fetches an individual object on the resource.
        
        This needs to be implemented at the user level. If the object can not
        be found, this should raise a ``NotFound`` exception.
        
        ``ModelResource`` includes a full working version specific to Django's
        ``Models``.
        """
        raise NotImplementedError()
    
    def cached_obj_get(self, request=None, filters={}):
        """
        A version of ``obj_get`` that uses the cache as a means to get
        commonly-accessed data faster.
        """
        cache_key = self.generate_cache_key('detail', filters)
        bundle = self._meta.cache.get(cache_key)
        
        if bundle is None:
            bundle = self.obj_get(request, filters)
            self._meta.cache.set(cache_key, bundle)
        
        return bundle
    
    def obj_create(self, bundle, request=None, filters={}):
        """
        Creates a new object based on the provided data.
        
        This needs to be implemented at the user level.
        
        ``ModelResource`` includes a full working version specific to Django's
        ``Models``.
        """
        raise NotImplementedError()
    
    def obj_update(self, bundle, request=None, filters={}):
        """
        Updates an existing object (or creates a new object) based on the
        provided data.
        
        This needs to be implemented at the user level.
        
        ``ModelResource`` includes a full working version specific to Django's
        ``Models``.
        """
        raise NotImplementedError()
    
    def obj_delete_list(self, request=None, filters={}):
        """
        Deletes an entire list of objects.
        
        This needs to be implemented at the user level.
        
        ``ModelResource`` includes a full working version specific to Django's
        ``Models``.
        """
        raise NotImplementedError()
    
    def obj_delete(self, request=None, filters={}):
        """
        Deletes a single object.
        
        This needs to be implemented at the user level.
        
        ``ModelResource`` includes a full working version specific to Django's
        ``Models``.
        """
        raise NotImplementedError()

    def is_valid(self, bundle, request=None):
        """
        Handles checking if the data provided by the user is valid.
        
        Mostly a hook, this uses class assigned to ``validation`` from
        ``Resource._meta``.
        
        If validation fails, an error is raised with the error messages
        serialized inside it.
        """
        errors = self._meta.validation.is_valid(bundle, request)
        
        if len(errors):
            if request:
                desired_format = self.determine_format(request)
            else:
                desired_format = self._meta.default_format
            
            serialized = self.serialize(request, errors, desired_format)
            response = HttpBadRequest(content=serialized, content_type=build_content_type(desired_format))
            raise ImmediateHttpResponse(response=response)
    
    def rollback(self, bundles):
        """
        Given the list of bundles, delete all objects pertaining to those
        bundles.
        
        This needs to be implemented at the user level. No exceptions should
        be raised if possible.
        
        ``ModelResource`` includes a full working version specific to Django's
        ``Models``.
        """
        raise NotImplementedError()

    # Views.

    def show(self, request, filters, format):
        """
        Returns a single serialized resource.
        
        Calls ``cached_obj_get/obj_get`` to provide the data, then handles that result
        set and serializes it.
        
        Should return a HttpResponse (200 OK).
        """
        try:
            obj = self.cached_obj_get(request, filters)
        except ObjectDoesNotExist:
            return HttpGone()
        except MultipleObjectsReturned:
            return HttpMultipleChoices("More than one resource is found at this URI.")
        
        bundle = self.full_dehydrate(obj)
        return self.create_response(request, bundle)

    def update(self, request, filters, format):
        """
        Either updates an existing resource or creates a new one with the
        provided data.
        
        Calls ``obj_update`` with the provided data first, but falls back to
        ``obj_create`` if the object does not already exist.
        
        If a new resource is created, return ``HttpCreated`` (201 Created).
        If an existing resource is modified, return ``HttpAccepted`` (204 No Content).
        """
        deserialized = self.deserialize(request, request.raw_post_data, format=format)
        bundle = self.build_bundle(data=dict_strip_unicode_keys(deserialized))
        self.is_valid(bundle, request)
        
        try:
            updated_bundle = self.obj_update(bundle, request=request, pk=filters.get('pk'))
            return HttpAccepted()
        except:
            updated_bundle = self.obj_create(bundle, request=request, pk=filters.get('pk'))
            return HttpCreated(location=self.get_resource_uri(updated_bundle))

    def create(self, request, filters, format):
        """
        Creates a new subcollection of the resource under a resource.
        
        This is not implemented by default because most people's data models
        aren't self-referential.
        
        If a new resource is created, return ``HttpCreated`` (201 Created).
        """
        return HttpNotImplemented()

    def destroy(self, request, filters, format):
        """
        Destroys a single resource/object.
        
        Calls ``obj_delete``.
        
        If the resource is deleted, return ``HttpAccepted`` (204 No Content).
        If the resource did not exist, return ``HttpGone`` (410 Gone).
        """
        try:
            self.obj_delete(request, filters)
            return HttpAccepted()
        except NotFound:
            return HttpGone()

    def options(self, request, format):
        raise NotImplementedError()
    
    def patch(self, request, filters, format):
        raise NotImplementedError()

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

    def get_resource_uri(self, bundle_or_obj, format=None):    
        if isinstance(bundle_or_obj, bundle.Bundle):
            obj = bundle_or_obj.obj
        else:
            obj = bundle_or_obj
        
        if format:
            format = '.' + format
        else:
            format = ''
        
        filters = re.compile(self._meta.parsed_route).groupindex
        if '__format' in filters:
            del filters["__format"]
        for attr in filters:
            filters[attr] = utils.traverse(obj, attr)  
        
        return reverse(self.name, kwargs=filters) + format

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

        bundle = self.full_dehydrate(obj)
        return bundle


class Collection(object):
    # Views.
    # NOTE: STRAIGHT COPY-PASTE FROM TASTYPIE
    # WILL NEED WORK TO CONVERT TO THE NEW ROUTER    
    def show(self, request, filters, format):
        """
        Returns a serialized list of resources.
        
        Calls ``obj_get_list`` to provide the data, then handles that result
        set and serializes it.
        
        Should return a HttpResponse (200 OK).
        """
        # TODO: Uncached for now. Invalidation that works for everyone may be
        #       impossible.
        objects = self.obj_get_list(request, filters)
        sorted_objects = self.apply_sorting(objects, options=request.GET)
        
        paginator = Paginator(request.GET, sorted_objects, resource_uri=self.get_resource_list_uri(),
           limit=self._meta.limit)
        to_be_serialized = paginator.page()
        
        # Dehydrate the bundles in preparation for serialization.
        to_be_serialized['objects'] = [self.full_dehydrate(obj=obj) for obj in to_be_serialized['objects']]
        return to_be_serialized

    def update(self, request, filters, format):
        """
        Replaces a collection of resources with another collection.
        
        Calls ``delete_list`` to clear out the collection then ``obj_create``
        with the provided the data to create the new collection.
        
        Return ``HttpAccepted`` (204 No Content).
        """
        deserialized = self.deserialize(request, request.raw_post_data, format=request.META.get('CONTENT_TYPE', 'application/json'))
        
        if not 'objects' in deserialized:
            raise BadRequest("Invalid data sent.")
        
        self.obj_delete_list(request=request, **self.remove_api_resource_names(kwargs))
        bundles_seen = []
        
        for object_data in deserialized['objects']:
            bundle = self.build_bundle(data=dict_strip_unicode_keys(object_data))
            
            # Attempt to be transactional, deleting any previously created
            # objects if validation fails.
            try:
                self.is_valid(bundle, request)
            except ImmediateHttpResponse:
                self.rollback(bundles_seen)
                raise
            
            self.obj_create(bundle, request=request)
            bundles_seen.append(bundle)
        
        return HttpAccepted()

    def create(self, request, filters, format):
        """
        Creates a new resource/object with the provided data.
        
        Calls ``obj_create`` with the provided data and returns a response
        with the new resource's location.
        
        If a new resource is created, return ``HttpCreated`` (201 Created).
        """
        deserialized = self.deserialize(request, request.raw_post_data, format=request.META.get('CONTENT_TYPE', 'application/json'))
        bundle = self.build_bundle(data=dict_strip_unicode_keys(deserialized))
        self.is_valid(bundle, request)
        updated_bundle = self.obj_create(bundle, request=request)
        return HttpCreated(location=self.get_resource_uri(updated_bundle))

    def destroy(self, request, filters, format):
        """
        Destroys a collection of resources/objects.
        
        Calls ``obj_delete_list``.
        
        If the resources are deleted, return ``HttpAccepted`` (204 No Content).
        """
        self.obj_delete_list(request=request, **self.remove_api_resource_names(kwargs))
        return HttpAccepted()


class ModelCollection(Collection):
    def get_resource_uri(self, bundle_or_obj, format=None):
        for base in self.__class__.__bases__:
            if issubclass(base, Resource) and base not in [Resource, ModelResource]:
                return base().get_resource_uri(bundle_or_obj, format)

    #def show(self, request, filters, format):
    #    objs = self.obj_get_list(request, filters)
    #    return [obj.__dict__ for obj in objs]


# Based off of ``piston.utils.coerce_put_post``. Similarly BSD-licensed.
# And no, the irony is not lost on me.
def convert_post_to_put(request):
    """
    Force Django to process the PUT.
    """
    if request.method == "PUT":
        if hasattr(request, '_post'):
            del request._post
            del request._files
        
        try:
            request.method = "POST"
            request._load_post_and_files()
            request.method = "PUT"
        except AttributeError:
            request.META['REQUEST_METHOD'] = 'POST'
            request._load_post_and_files()
            request.META['REQUEST_METHOD'] = 'PUT'
            
        request.PUT = request.POST
    
    return request