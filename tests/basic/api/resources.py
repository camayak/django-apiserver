from django.contrib.auth.models import User
from apiserver import fields
from apiserver.resources import ModelResource
from apiserver.authorization import Authorization
from basic.models import Note


class UserResource(ModelResource):
    class Meta:
        route = '/users'
        queryset = User.objects.all()
        authorization = Authorization()


class NoteResource(ModelResource):
    user = fields.ForeignKey(UserResource, 'user')
    
    class Meta:
        route = '/notes'
        queryset = Note.objects.all()
        authorization = Authorization()
