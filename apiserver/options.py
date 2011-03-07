from django.conf import settings

from tastypie.authentication import Authentication
from tastypie.authorization import ReadOnlyAuthorization
from tastypie.cache import NoCache
from tastypie.throttle import BaseThrottle
from tastypie.validation import Validation

from apiserver.serializers import Serializer

class ResourceOptions(object):
    """
    A configuration class for ``Resource``.
    
    Provides sane defaults and the logic needed to augment these settings with
    the internal ``class Meta`` used on ``Resource`` subclasses.
    """
    serializer = Serializer()
    authentication = Authentication()
    authorization = ReadOnlyAuthorization()
    cache = NoCache()
    throttle = BaseThrottle()
    validation = Validation()
    #allowed_methods = ['get', 'post', 'put', 'delete']
    #list_allowed_methods = None
    #detail_allowed_methods = None
    limit = getattr(settings, 'API_LIMIT_PER_PAGE', 20)
    #api_name = None
    #resource_name = None
    #urlconf_namespace = None
    route = None
    default_format = 'application/json'
    filtering = {}
    ordering = []
    object_class = None
    queryset = None
    fields = []
    excludes = []
    include_resource_uri = True
    include_absolute_url = False
    
    def __new__(cls, meta=None):
        overrides = {}
        
        # Handle overrides.
        if meta:
            for override_name in dir(meta):
                # No internals please.
                if not override_name.startswith('_'):
                    overrides[override_name] = getattr(meta, override_name)
               
        return object.__new__(type('ResourceOptions', (cls,), overrides))