# -*- coding: utf-8 -*-

from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.core.urlresolvers import reverse_lazy
from django.conf import settings


def require_login(view):
    def check_permission(req, *args, **kwargs):
        if not req.user:
            return HttpResponseRedirect(reverse_lazy("login"))
        return view(req, *args, **kwargs)
    return check_permission


def require_dn(dn, view):
    def check_permission(req, *args, **kwargs):
        if not req.user:
            return HttpResponseRedirect(reverse_lazy("login"))
        if not req.user.match_dn(dn):
            return HttpResponseForbidden()
        return view(req, *args, **kwargs)
    return check_permission
