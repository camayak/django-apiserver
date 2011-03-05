# encoding: utf-8

import models
from fixture_generator import fixture_generator

@fixture_generator(models.Organization)
def test_organizations():
    models.Organization.objects.create(name="ACME")
    models.Organization.objects.create(name="REX")

@fixture_generator(models.Person, requires=['organization.test_organizations', ])
def test_people():
    one, two = models.Organization.objects.all()
    models.Person.objects.create(first_name="Stijn", last_name="Debrouwere", organization=one)
    models.Person.objects.create(first_name="Daniel", last_name="Bachhuber", organization=two)