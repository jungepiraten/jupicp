from random import choice
import string
import json

import django.core.mail
from django.views.generic import View
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied


def generate_password(length=8):
    return ''.join(choice(string.letters + string.digits) for _ in xrange(length))


def send_mail(data, options, recipient):
    if type(recipient) != list:
        recipient = [recipient]
    django.core.mail.send_mail(data['subject'], data['body'].format(**options), data['from'], recipient)


def classview_decorator(decorator):
    def wrapper(cls):
        cls.dispatch = decorator(cls.dispatch)
        return cls
    return wrapper


def raise_404(method):
    def wrap(*args, **kwargs):
        from django.core.exceptions import ObjectDoesNotExist
        from django.http import Http404
        try:
            return method(*args, **kwargs)
        except ObjectDoesNotExist, ex:
            raise Http404(ex.message)
    return wrap


class JSONView(View):
    def dispatch(self, *args, **kwargs):
        result = super(JSONView, self).dispatch(*args, **kwargs)
        if isinstance(result, HttpResponse):
            return result
        else:
            return HttpResponse(json.dumps(result), content_type="application/json")
