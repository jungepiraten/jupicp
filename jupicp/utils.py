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

def raise_404(original_class):
	original_dispatch = original_class.dispatch

	def dispatch(self, *args, **kwargs):
		from django.core.exceptions import ObjectDoesNotExist
		from django.http import Http404
		try:
			return original_dispatch(self, *args, **kwargs)
		except ObjectDoesNotExist, ex:
			raise Http404(ex.message)

	original_class.dispatch = dispatch
	return original_class

class JSONView(View):
	def get(self, request, *args, **kwargs):
		context = self.get_context_data(*args, **kwargs)
		return HttpResponse(json.dumps(context), content_type="application/json")
