`django-apiserver` is a proof-of-concept API generator for Django, reusing all the internals from Tastypie but replacing its routing and views system with one more akin to regular views. This is not a usable piece of software; it is an experiment. That said, if it were an actual piece of software, below is how the README would look.

---

`django-apiserver` is a RESTful and HATEOAS-compliant API generator for Django. APIServer distinguishes itself from other Django API generators by its more explicit, less magical approach to API generation. It comes with a bunch of sensible defaults and works well with Django models, but refrains from guessing your intentions.

In addition to serving up RESTful resources, the APIServer can create an API explorer for you, complete with documentation.

`django-apiserver` is a fork of `django-tastypie`, retaining most of its internals but with a new view and view routing system on top of it. Apiserver's `Resource` and `ModelResource` classes are more akin to Railsy class-based controllers, but serialization, deserialization, integration with Django models, model filtering, throttling, authorization and authentication all work similar or identical to Tastypie. Because, let's be honest, Tastypie is pretty good at all that.

`django-apiserver` can transparently support any number of serialization formats, but consciously provides only JSON (for data) and ATOM (for feeds) out of the box.

It's a well-kept secret that your average API generator only supports XML by pretending it works just like JSON. It doesn't. JSON doesn't cleanly map to XML, and rather than providing second-rate XML out of the box, we'd prefer to have developers focus on creating the best possible end-user experience, using the best possible formats. One less format to worry about, one less format to explain in your documentation.

This application requires Django 1.3.

Learn more and get started by browsing the full documentation.