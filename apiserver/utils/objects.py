# encoding: utf-8

from django.db import models


def traverse(obj, attr_string):
    attrs = attr_string.split("__")
    for attr in attrs:
        obj = getattr(obj, attr)
    
    if isinstance(obj, models.Model):
        obj = obj.pk
     
    return obj
    

def extract(key, dict):
    value = dict[key]
    del dict[key]
    return value, dict