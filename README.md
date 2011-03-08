`django-apiserver` is a proof-of-concept API generator for Django, reusing all the internals from Tastypie but replacing its routing and views system with one more akin to regular views. 

Because of its `django-tastypie` pedigree, APIServer is thoroughly RESTful and HATEOAS-compliant. APIServer distinguishes itself from other Django API generators by its more explicit, less magical approach to API generation, notably by requiring manual URL routing and splitting out list and
detail resources.

In addition to serving up RESTful resources, the APIServer will be able to an API explorer for you, complete with documentation.

APIServer's `Resource`, `ModelResource` and `CollectionResource` classes are more akin to Railsy class-based controllers than what you know from Tastypie or Piston, but serialization, deserialization, integration with Django models, model filtering, throttling, authorization and authentication all work similarly or identical to Tastypie. Because, let's be honest, Tastypie is pretty good at all that.

`django-apiserver` can transparently support any number of serialization formats, but consciously provides only JSON (for data) and, soon, ATOM (for feeds) out of the box.

It's a well-kept secret that your average API generator only supports XML by pretending it works just like JSON. It doesn't. JSON doesn't cleanly map to XML, and rather than providing second-rate XML out of the box, we'd prefer to have developers focus on creating the best possible end-user experience, using the best possible formats. One less format to worry about, one less format to explain in your documentation.

This application requires Django 1.3.

Learn more and get started by browsing the full documentation. (Which we don't have yet, this being a proof-of-concept and all.)