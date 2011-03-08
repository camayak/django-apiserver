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
    
    def show(self, request, filters, format):
        return {"message": ["hello there", "cowboy"]}


# regular model resource
class Everybody(api.ModelResource):
    class Meta:
        route = '/everybody/<pk:#>'
        queryset = organization.Person.objects.all()


# model resource
class Organization(api.ModelResource):
    people = api.fields.ToManyField('organization.resources.Person', 'people')

    class Meta:
        route = '/organizations/<name:s>'
        queryset = organization.Organization.objects.all()

# collection resource
class Organizations(api.ModelCollection, Organization):
    class Meta(Organization.Meta):
        route = '/organizations'


# deep model resource
class Person(api.ModelResource):
    organization = api.fields.ToOneField(Organization, 'organization')

    class Meta:
        route = '/organizations/<organization__name:s>/people/<pk:#>'
        queryset = organization.Person.objects.all()


# deep collection resource
class People(api.ModelCollection, Person):
    class Meta(Person.Meta):
        route = '/organizations/<org:s>/people'
            
    # shows how you could customize the args or do other wacky things
    # 
    # this example transforms the filter args, and uppercases the org name
    # before handing it off
    def show(self, request, filters, format):
        organization, filters = api.utils.extract('org', filters)
        filters['organization__name'] = organization.upper()
        return super(People, self).show(request, filters, format)