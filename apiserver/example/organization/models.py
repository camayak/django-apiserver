# encoding: utf-8

from django.db import models

class Organization(models.Model):
    name = models.CharField(max_length=100)

class Person(models.Model):
    organization = models.ForeignKey(Organization, related_name='people')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)