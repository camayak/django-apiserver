from django.conf.urls.defaults import *

import apiserver as api
import organization

class TOC(api.TOC):
    class Meta:
        route = ''
        resources = [organization.resources.Organizations]

v1 = api.API('v1')
v1.register(TOC)
v1.register(organization.resources)

urlpatterns = patterns('',
    (r'^', include(v1.urlconf)),
)