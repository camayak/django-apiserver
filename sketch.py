# My ideal API construction process (very rough, all-over-the-place draft)

from django.contrib import syndication

# Resources

class re(str):
    pass

class CollectionResource(object):
    name = "Collection feed"

    # we'd only actually make a feed if the resource has a 
    # item_title method defined -- can't make a feed without a title
    def make_feed(this):
        class Feed(syndication.views.Feed):
            title = this.__class__.__name__.lower() + " feed"
        
            def items(self):
                # we could use a ?limit arg to limit things
                return this.get_query_set()
        
            def item_title(self, item):
                return this.item_title(name)
        
            def item_description(self, item):
                return this.item_description(description)

        return Feed

    def item_description(self):
        return ''

class Schmoe(api.Resource):
    # routes are passed through surlex by default, but not if you explicitly
    # specify a regex as the route
    route = re('^/people$')

    # AUTH: one way of authenticating users (esp. useful for non-model resources, where row-level ACL doesn't make sense)
    @api.requires(roles.EDITOR)
    def show(self, name):
        do_something()
    
    # if you have no need for overwriting the resource
    api.requires(roles.WRITER, delete)

class People(api.CollectionResource):
    # gets passed the same keyword arguments as show, create, update, destroy
    def get_query_set(self, request, organization):
        # preprocessing can easily happen with a custom manager
        # -- note that specifically for authentication and authorization, you can also use
        # the right meta properties w/ Tastypie Authorization and Authentication classes
        return models.Person.authorize(user).filter(organization=organization).all()

    # gets passed the same keyword arguments as show, create, update, destroy, 
    # but the queryset will be the first argument
    def process_query_set(self, queryset, **kwargs):
        # handling authentication or whatever if it requires turning the queryset into a list
        # (and thus should be at the end of the line)
        return ACL(qs)  
        
class Person(api.ModelResource):
    collection = People

    def get_title(self, obj):
        return obj.name
    
    def get_description(self, obj):
        return obj.bio

# how URL routing would work:

def soak_errors(fn):
    try:
        fn()
    except:
        return {
            "error": "Internal server error", 
            "message": "Sorry, we can't serve your request at this time."            
        }

# we should do this for the default ModelResource, nobody needs to see our internal error message traces
# -- however, because people can add their own decorators, we have to make sure that this is always the
# outer wrapper -- so perhaps we need this as a metaclass, or just during __init__
@on_error(BaseException, 500, soak_errors)
class ModelResource(object):
    class FilterSet(api.FilterSet):
        pass

    # create, update etc. all pass through this for a modelresource
    def get_filtered_query_set(self, request, **kwargs):
        # filter by keyword args that come through the URL
        qs = qs.filter(**kwargs)
        # in addition, filter by get args with Alex Gaynor's django-filter
        qs = self.FilterSet(request.GET, queryset=qs)
        
        return qs

    def show(self, request, **kwargs):
        qs = self.get_filtered_query_set(**kwargs)
        return qs_to_repr(qs)

class Organization(api.CollectionResource):
    collection = Organizations
    route = '/organizations/<type:s>/<uuid:s>/'
    
    # if you can't (or don't want to) cleanly map route args 
    # to filter args, overrides can save the day
    def get_filtered_query_set(self, **kwargs):
        kwargs['type__name'] = org_type
        del kwargs['type']
        super(Organization, self).get_filtered_query_set(self, **kwargs)

# shows QS filtering

def add_response_time(fn):
    response = fn()
    response["meta"] = {"response_time": 550}
    return response

@on_view(add_response_time)         # add_response_time will be wrapped around show, create, update, destroy
class Account(api.ModelResource):
    class FilterSet(api.FilterSet):
        class Meta:
            fields = ['name', 'age', 'age__lt', 'age__gt', 'user__email']

    def create(self):
        raise NotImplementedError()

    # perhaps this is better, if we wish to support OPTIONS
    create = None

    failure = lambda: {"error": "This doesn't work."}
    
    @on_error(PermissionError, 403, failure)
    def destroy(self):
        raise PermissionError()
        
# stuff that we'll handle in exactly the same way as Tastypie

class Note(api.ModelResource):
    # not in class Meta, because this would make it more difficult to do selective overrides
    authentication = FancyAuth()
    authorization = FancyAuthorization()
    validation = Validation()
    cache = SimpleCache()

## app ##
import apiserver

from organizations import deprecated_resources as organizations
import publications
from roles.resources import Role

# namespace your API
api = apiserver.API('v1')
# initialize an API explorer
explorer = apiserver.Explorer(api)
# register a module
api.register(organizations)
api.register(publications.resources)
# register a single resource
api.register(Role)

## urls.py ##
from app import api

urlpatterns = patterns('',
    (r'^', include(api.urls)),
    (r'^v1/explorer/$', include(explorer.urls)),
)

# doc generator (potentially a derivative / enhancement of sphinx.autodoc)
# python manage.py generate_apidocs