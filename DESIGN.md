What I do like about Tastypie
=============================

* meta information as part of the response, pagination (tastypie.paginator)
* Content type negotiation with the Accepts header
* registration of resources into a namespace
* hydration/dehydration and serialization in general (tastypie.serializers.Serializer and tastypie.fields, full_hydrate and full_dehydrate in tastypie.resources)
* input validation
* the way it handles foreign keys and m2ms. (tastypie.fields)
* modelresource should be built entirely on resource -- a subclass, not an entirely different way of doing things
* URI-based / HATEOAS-compatible
* authentication and authorization (though I also like my decorator-based approach from flask-apiserver)
* caching, throttling, API-key auth
* discovery
* the fact that you can make resources for third-party classes, since you don't need to touch the original code.
* the way it handles errors is pretty good (still outputting JSON except for the most fatal of errors) although I'd never send along a stack trace -- those should be for internal logs only.
* OPTIONS support (recently)

Where I would deviate from Tastypie
===================================

* We should probably stick to JSON throughout. Tastypie's YAML and XML support, as with most of these "multi-output" API generators, is poor, and is silly because you'll only want to document / use a single format in the documentation anyway out of time constraints, you'll want to encourage a single format because it makes things easier to cache et cetera. XML is particularly tricky, because it has nothing like "anonymous arrays" and "anonymous objects" meaning you'll either have to litter your XML with "items" containers, or make sure you can add in a pluralized name for each resource, which isn't always easy. It'll keep the code leaner as well. If anything, in addition to JSON we'd want ATOM, not XML, not YAML.
* The URL construction is too magical. Automatically making /schema/, setting up all the CRUD ops and creating both list and detail is all fine, but it shouldn't be a black box. I want to be able to use deep URL structures and keyword arguments. The resource construction shouldn't hide away the routing.
* If you're able to refer to foreign keys with a resource URI, you should be able to filter on resource URIs as well, to keep things aligned with how Django works.
* It should follow Rails' terminology, since that's what people are familiar with and there's no use inventing something new. It should feel more like a natural extension of class-based views. (so e.g. a view shouldn't return a queryset, it should pass a serializable object to api.formatted_response and return that, leaving full flexibility for custom serialization etc.
* Lists and details are conceptually separate resources (one's a bucket, the other's a thing), so while it should be easy to create both simultaneously with a minimal amount of code, they shouldn't be bunched up into a single resource. A schema is a separate resource too.
* Instead of list_allowed_methods and detail_allowed_methods, you should just override the methods you don't want to expose and raise a NotImplementedError there. Cleaner and more obvious.
* I really like how Tastypie allows you to smoothly filter querysets, being able to specify which filters to allow et cetera. However, I would much rather implement this on top of Alex Gaynor's `django-filter` than reinvent the wheel.
* Tastypie's error codes are off. It confuses 401s with 403s, and returns 410s in some cases where it should return 404s.
* I want surlex, not regexes and not magical route creation

What Tastypie lacks
===================

* Ability to fetch a resource either through the accepts header or by suffixing the right extension (.json, .atom) -- no ?format tomfoolery.
* Full vs. HATEOAS by suffixing /full/ to a resource, e.g. /stories/33/full/ or /stories/full/ for the list.
* Support for ATOM feeds.
* Support for microformats (when your data / models can be easily mapped to a microformat)
* The ability to show all possible routes (Tastypie only shows the "base" ones, but sometimes it's useful to get a birds-eye overview.)
* The ability to specify whether we want HATEOAS behavior or whether we want to include all subresources (handy for quick integrations and exploration)
* Only fetch specific fields (w/ `Django's qs.only(*fields).only(pk)`) -- though be aware that this could adversely impact cacheability.
* A way to specify which detail resource should be used when handling related resources (if e.g. multiple ModelResource classes work on the same Person model, each representing part of it -- a model can sometimes be an implementation detail and not always map neatly to a resource)
* The ability to register either separate resources -or- an entire module.
* It should have an API explorer out of the box.
* It should also be autodocumenting, though with ample opportunity to pass in narrative docs as well. (e.g. as document docstrings).
* PATCH support
* read-only / calculated / included-from-elsewhere fields (?) w/ errors when people try to change them
* Aggregated data on response times, failed authentication, failed authorization etc. globally, per view and per request.

What we'll forego
=================

* XML serialization, as mentioned. (Not because we're feeling combative, but because treating XML as a first-class serialization format is hard.)
* arbitrary result sets (bad for cacheability)
* schema definitions (nice but gimmicky)