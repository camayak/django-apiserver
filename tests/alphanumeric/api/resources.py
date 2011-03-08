from apiserver.authorization import Authorization
from apiserver.fields import CharField
from apiserver.resources import ModelResource
from alphanumeric.models import Product


class ProductResource(ModelResource):
    class Meta:
        resource_name = 'products'
        queryset = Product.objects.all()
        authorization = Authorization()
