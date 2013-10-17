# -*- coding: utf-8 -*-

from django.conf import settings

class SetAuthentificated:
	def process_request(self, request):
		request.user = settings.DIRECTORY.get_user(request.session["user"]) if "user" in request.session else None
