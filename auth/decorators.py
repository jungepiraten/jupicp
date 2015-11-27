# -*- coding: utf-8 -*-

from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.core.urlresolvers import reverse_lazy
from django.conf import settings

import urllib


def require_login(view):
    def check_permission(req, *args, **kwargs):
        if not req.user:
            redirect_url = req.META["RAW_URI"]
            return HttpResponseRedirect("{}?redirect={}".format(reverse_lazy("login"), urllib.quote(redirect_url)))
        return view(req, *args, **kwargs)
    return check_permission


def require_dn(dn, view):
    def check_permission(req, *args, **kwargs):
        if not req.user:
            redirect_url = req.META["RAW_URI"]
            return HttpResponseRedirect("{}?redirect={}".format(reverse_lazy("login"), urllib.quote(redirect_url)))
        if not req.user.match_dn(dn):
            return HttpResponseForbidden()
        return view(req, *args, **kwargs)
    return check_permission
