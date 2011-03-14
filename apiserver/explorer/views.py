# encoding: utf-8

import re
import urllib2
import functools
import simplejson
from copy import copy
from pygments import lexers, formatters, highlight

from django.contrib.auth.models import User
from django.views.generic.simple import direct_to_template
from django.test.client import Client
from django import forms

from utils.authentication import create_auth_string

api = Client()
api.put = functools.partial(api.post, REQUEST_METHOD='PUT')

# TODO: genericize this so users can provide their own "auto-password fill-in" mechanism for testing
def get_password(username):
    return username.split("@")[0]

test_users = {}
for user in User.objects.all():
    test_users[user.username] = get_password(user.username)
user_choices = zip(test_users.keys(), test_users.keys())


def get_base_uris(base):
    content = api.get(base).content
    data = simplejson.loads(content)
    uridict = data.values()
    return [uri["list_endpoint"] for uri in uridict]

default_user = ("dunno", "yet")

HEADERS = {
    "HTTP_AUTHORIZATION": create_auth_string(*default_user),
    "HTTP_CONTENT_TYPE": "application/json",
    "HTTP_ACCEPT": "application/json",
    }

METHODS = (
    ('get', 'GET'),
    ('post', 'POST'),
    ('put', 'PUT'),
    ('delete', 'DELETE'),
    )


class RequestForm(forms.Form):
    method = forms.ChoiceField(choices=METHODS, initial='GET', required=False)
    endpoint = forms.CharField(max_length=200, initial='/v1/', required=False)
    user = forms.ChoiceField(choices=user_choices, initial=default_user[0], required=False)
    data = forms.CharField(widget=forms.widgets.Textarea, initial='', required=False)


def linkify(thing):
    return '&quot;<a href="?endpoint={link}">{link}</a>&quot;'.format(link=thing.group(1))


def prettify(json):
    json = simplejson.loads(json)
    json = simplejson.dumps(json, sort_keys=True, indent=4)
    lexer = lexers.get_lexer_by_name("javascript")
    formatter = formatters.HtmlFormatter()
    html = highlight(json, lexer, formatter)
    return re.sub('&quot;(/.+/)&quot;', linkify, html)


def explorer(request):
    if request.POST:
        form = RequestForm(request.POST)
        if form.is_valid():
            method = form.cleaned_data['method']
        else:
            method = "get"
    else:
        form = RequestForm()
        method = "get"

    post_endpoint = request.POST.get("endpoint", False)
    querystring_endpoint = request.GET.get("endpoint", "/v1/")
    endpoint = post_endpoint or querystring_endpoint
    form.fields.get('endpoint').initial = endpoint
    
    user = form.data.get("user", default_user[0])
    pwd = test_users[user]
    headers = copy(HEADERS)
    headers["HTTP_AUTHORIZATION"] = create_auth_string(user, pwd)
    print "Relaying {method} request for {user} to {endpoint}".format(user=user, endpoint=endpoint, method=method.upper())
    
    response = getattr(api, method)(endpoint, data=form.data.get('data', ''), content_type='application/json', **headers)
    status_code = response.status_code
    try:
        response = prettify(response.content)
    except simplejson.JSONDecodeError:
        response = response.content

    return direct_to_template(request, "explorer.html", {
        "starting_points": get_base_uris('/v1/'),
        "path": request.META["HTTP_HOST"],
        "endpoint": endpoint,
        "form": form,
        "headers": headers,
        "status": status_code,
        "response": response,
        "method": method,
        "username": user,
        "password": get_password(user),
        "data": form.data.get("data", ""),
        })
