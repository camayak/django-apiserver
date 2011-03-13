from django.conf.urls.defaults import *
from core.tests.api import Api, NoteResource, UserResource


api = API()
api.register(NoteResource)
api.register(UserResource)

urlpatterns = patterns('',
    (r'^api/', include(api.urls)),
)
