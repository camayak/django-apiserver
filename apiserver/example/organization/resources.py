# encoding: utf-8

import apiserver as api
from organization import models as organization

"""
Visit these URLs to see how it works:
- /organizations.json 
- /organizations/acme/people.json
- /organizations/ACME/people/1.json
- /organizations/REX/people/2.json

Differences from Tastypie
- url routing is entirely manual, no magic
- show/create/update/destroy methods (stolen from Rails)
  that return a data structure (e.g. a dict)
- separate collection resources
- no ?format arg, but .<format> appended to routes
  (Although using Accepts should still be encouraged.)

Any other differences (e.g. no Meta, no hydrate/dehydrate)
purely for the sake of being able to quickly put together
a prototype.
"""

# regular resource
class Message(api.Resource):
    class Meta:
        route = '/messages/<name:s>'
    
    def show(self, request, **kwargs):
        print kwargs
        return {"message": ["hello there", "cowboy"]}


# regular model resource
class Everybody(api.ModelResource):
    class Meta:
        route = '/everybody/<pk:#>'
        queryset = organization.Person.objects.all()


# model resource
class Organization(api.ModelResource):
    class Meta:
        route = '/organizations/<name:s>'
        queryset = organization.Organization.objects.all()


# collection resource
class Organizations(Organization, api.CollectionResource):
    class Meta(Organization.Meta):
        route = '/organizations'


def transform(filters, old, new, fn):
    filters[new] = fn(filters[old])
    del filters[old]
    return filters


# deep collection resource
class People(api.CollectionResource):
    class Meta:
        route = '/organizations/<org:s>/people'
        queryset = organization.Person.objects.all()
            
    # shows how you could customize the args or do other wacky things
    # 
    # this example transforms the filter args, and uppercases the org name
    # before handing it off
    def show(self, request, filters, format):
        filters = transform(filters, 'org', 'organization__name', lambda name: name.upper())
        return super(People, self).show(request, filters, format)


# deep model resource
# this one inherits the other way around (from list to detail instead of from detail to list)
# which works just as well
class Person(People, api.ModelResource):
    class Meta(People.Meta):
        route = '/organizations/<organization__name:s>/people/<pk:#>'
        queryset = organization.Person.objects.all()

    # resource URI test -- see apiserver.resources for implementation;
    # like tastypie, easily overridable by just overloading
    # get_resource_uri
    def show(self, request, filters, format):
        representation = super(Person, self).show(request, filters, format)
        representation['uri'] = self.get_resource_uri(self.obj_get(filters=filters), format)
        return representation