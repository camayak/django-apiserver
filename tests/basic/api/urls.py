from django.conf.urls.defaults import *
from apiserver.api import Api
from basic.api.resources import NoteResource, UserResource

api = API(api_name='v1')
api.register(NoteResource(), canonical=True)
api.register(UserResource(), canonical=True)

urlpatterns = api.urls
