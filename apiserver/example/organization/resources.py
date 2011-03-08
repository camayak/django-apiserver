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


# collection resource
class Organizations(api.ModelCollectionResource):
    class Meta:
        route = '/organizations'
        queryset = organization.Organization.objects.all()


# model resource
class Organization(Organizations, api.ModelResource):
    class Meta(Organizations.Meta):
        route = '/organizations/<name:s>'


# deep collection resource
class People(api.ModelCollectionResource):
    class Meta:
        route = '/organizations/<org:s>/people'
        queryset = organization.Person.objects.all()
            
    # shows how you could customize the args or do other wacky things
    # 
    # this example transforms the filter args, and uppercases the org name
    # before handing it off
    def show(self, request, filters, format):
        organization, filters = api.utils.extract('org', filters)
        filters['organization__name'] = organization.upper()
        return super(People, self).show(request, filters, format)


# deep model resource
class Person(People, api.ModelResource):
    class Meta(People.Meta):
        route = '/organizations/<organization__name:s>/people/<pk:#>'
        queryset = organization.Person.objects.all()
    
    # hmm, I don't like that this has to happen, though it's a direct
    # consequence of subclassing from the list resource
    # -- perhaps just subclassing Meta should be enough?
    def show(self, request, filters, format):
        return super(People, self).show(request, filters, format)