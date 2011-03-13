from django.conf.urls.defaults import *
from apiserver import fields
from apiserver.resources import ModelResource
from core.models import Note, Subject
from core.tests.api import Api, UserResource


class SubjectResource(ModelResource):
    class Meta:
        route = '/subjects'
        queryset = Subject.objects.all()


class CustomNoteResource(ModelResource):
    author = fields.ForeignKey(UserResource, 'author')
    subjects = fields.ManyToManyField(SubjectResource, 'subjects')
    
    class Meta:
        route = '/notes'
        queryset = Note.objects.all()


api = API(api_name='v1')
api.register(CustomNoteResource())
api.register(UserResource())
api.register(SubjectResource())

urlpatterns = patterns('',
    (r'^api/', include(api.urls)),
)
