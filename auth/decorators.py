# -*- coding: utf-8 -*-

from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.core.urlresolvers import reverse_lazy
from django.conf import settings

import urllib


def require_login(view):
    def check_permission(req, *args, **kwargs):
        if not req.user:
            return HttpResponseRedirect("{}?redirect={}".format(reverse_lazy("login"), urllib.urlencode(self.request.META["RAW_URI"])))
        return view(req, *args, **kwargs)
    return check_permission


def require_dn(dn, view):
    def check_permission(req, *args, **kwargs):
        if not req.user:
            return HttpResponseRedirect("{}?redirect={}".format(reverse_lazy("login"), urllib.urlencode(self.request.META["RAW_URI"])))
        if not req.user.match_dn(dn):
            return HttpResponseForbidden()
        return view(req, *args, **kwargs)
    return check_permission
