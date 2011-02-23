"""
Where I would deviate from Tastypie:

* We should probably stick to JSON throughout. Tastypie's YAML and XML support, as with most of these "multi-output" API generators, is sorry-assed at best, and is silly because you'll only want to document / use a single format in the documentation anyway out of time constraints, you'll want to encourage a single format because it makes things easier to cache et cetera. XML is particularly tricky, because it has nothing like "anonymous arrays" and "anonymous objects" meaning you'll either have to litter your XML with "items" containers, or make sure you can add in a pluralized name for each resource, which isn't always easy. It'll keep the code leaner as well. If anything, in addition to JSON we'd want ATOM, not XML, not YAML.
* The URL construction is too magical. Automatically making /schema/, setting up all the CRUD ops and creating both list and detail is all fine, but it shouldn't be a black box. I want to be able to use deep URL structures and keyword arguments. The API construction shouldn't hide away the routing.
* If you're able to refer to foreign keys with a resource URI, you should be able to filter on resource URIs as well, to keep things aligned with how Django works.
* It should follow Rails' terminology, since that's what people are familiar with and there's no use inventing something new. It should feel more like a natural extension of class-based views. (so e.g. a view shouldn't return a queryset, it should pass a serializable object to api.formatted_response and return that, leaving full flexibility for custom serialization etc.
* Lists and details are conceptually separate resources (one's a bucket, the other's a thing), so while it should be easy to create both simultaneously with a minimal amount of code, they shouldn't be bunched up into a single resource.
* Instead of list_allowed_methods and detail_allowed_methods, you should just override the methods you don't want to expose and raise a NotImplementedError there. Cleaner and more obvious.
* I really like how Tastypie allows you to smoothly filter querysets, being able to specify which filters to allow et cetera. However, I would much rather implement this on top of Alex Gaynor's `django-filter` than reinvent the wheel.
* Tastypie's error codes are off. It confuses 401s with 403s, and returns 410s in some cases where it should return 404s.

(Most code that I'm not inclined to reuse lives in tastypie.api and tastypie.resources, though there are bits and bobs in those files which merit copy-pasting as well.)

What I do like about Tastypie:

* meta information as part of the response, pagination (tastypie.paginator)
* Content type negotiation with the Accepts header
* registration of resources into a namespace
* hydration/dehydration and serialization in general (tastypie.serializers.Serializer and tastypie.fields, full_hydrate and full_dehydrate in tastypie.resources)
* input validation
* the way it handles foreign keys and m2ms. (tastypie.fields)
* modelresource should be built entirely on resource -- a subclass, not an entirely different way of doing things
* URI-based / HATEOAS-compatible
* authentication and authorization (though I also like my decorator-based approach from flask-apiserver)
* caching, throttling, API-key auth
* discovery
* the fact that you can make resources for third-party classes, since you don't need to touch the original code.
* the way it handles errors is pretty good (still outputting JSON except for the most fatal of errors) although I'd never send along a stack trace -- those should be for internal logs only.
* OPTIONS support (recently)

What it lacks: 

* Ability to fetch a resource either through the accepts header or by suffixing the right extension (.json, .atom) -- no ?format tomfoolery.
* Support for (read-only) feeds.
* Support for microformats (when your data / models can be easily mapped to a microformat)
* The ability to show all possible routes (Tastypie only shows the "base" ones, but sometimes it's useful to get a birds-eye overview.)
* The ability to specify whether we want HATEOAS behavior or whether we want to include all subresources (handy for quick integrations and exploration)
* Only fetch specific fields (w/ Django's qs.only(*fields).only(pk)) -- though be aware that this could adversely impact cacheability.
* A way to specify which detail resource should be used when handling related resources (if e.g. multiple ModelResource classes work on the same Person model, each representing part of it -- a model can sometimes be an implementation detail and not always map neatly to a resource)
* The ability to register either separate resources -or- an entire module.
* It should have an API explorer out of the box.
* It should also be autodocumenting, though with ample opportunity to pass in narrative docs as well. (e.g. as document docstrings).
* PATCH support
* read-only / calculated / included-from-elsewhere fields (?) w/ errors when people try to change them
* Aggregated data on response times per view.

What I like/dislike about other systems:

* django-rest-framework conflates models and resources -- not good
* on the other hand, it clearly and cleanly exposes get, post, etc. as methods on the resource
* flask-apiserver nicely separates list and detail resources, and it also 
* I want surlex, not regexes

What we would also want, but is perhaps tangential to the API generator:

* sandboxing

What we'll forego: 

* XML serialization, as mentioned
* result sets (bad for cacheability)
* schema definitions (nice but gimmicky)

Strategy: try to get as much of the routing etc. in place, before we start adding in the stuff we borrow from Tastypie. That'll make it easier to keep track with feature updates in Tastypie.
"""

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
# register a base module (it expects a 'resources' variable to be present in __init__.py)
api.register(publications)
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