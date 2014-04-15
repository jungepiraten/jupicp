from random import choice
import string
import json

import django.core.mail
from django.views.generic import View
from django.http import HttpResponse

def generate_password(length=8):
	return ''.join(choice(string.letters + string.digits) for _ in xrange(length))

def send_mail(data, options, recipient):
	if type(recipient) != list:
		recipient = [recipient]
	django.core.mail.send_mail(data['subject'], data['body'].format(**options), data['from'], recipient)

def classview_dispatcher(function):
	def wrapper(original_class):
		original_dispatch = original_class.dispatch
		original_class.dispatch = function(original_dispatch)
		return original_class
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
	def get(self, request, *args, **kwargs):
		context = self.get_context_data(*args, **kwargs)
		return HttpResponse(json.dumps(context), content_type="application/json")

	def post(self, request, *args, **kwargs):
		context = self.do_action(*args, **kwargs)
		return HttpResponse(json.dumps(context), content_type="application/json")
