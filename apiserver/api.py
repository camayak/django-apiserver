# encoding: utf-8

import inspect
from django.conf.urls.defaults import patterns, url, include
from resources import Resource

class API(object):
    def __init__(self, version):
        self.urlconf = []
        self.patterns = []
        self.version = '^' + version.rstrip('/')
    
    def register(self, module):
        resources = [obj for name, obj in inspect.getmembers(module)
            if inspect.isclass(obj)
            and issubclass(obj, Resource)]
            
        for resource in resources:
            instance = resource()
            self.patterns.append(url(instance.route, instance.dispatch))

        self.urlconf += patterns('', (self.version, include(self.patterns)))
        
        print self.urlconf