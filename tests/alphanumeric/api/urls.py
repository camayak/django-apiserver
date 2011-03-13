from django.conf.urls.defaults import *
from apiserver.api import Api
from alphanumeric.api.resources import ProductResource

api = API(api_name='v1')
api.register(ProductResource(), canonical=True)

urlpatterns = api.urls
