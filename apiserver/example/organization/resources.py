import apiserver as api

# encoding: utf-8

class Person(api.Resource):
    route = '/people/<name:s>'
    
    def show(self, request, **kwargs):
        print kwargs
        return {"message": ["hello there", "cowboy"]}