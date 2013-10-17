from random import choice
import string

import django.core.mail

def generate_password(length=8):
	return ''.join(choice(string.letters + string.digits) for _ in xrange(length))

def send_mail(data, options, recipient):
	if type(recipient) != list:
		recipient = [recipient]
	django.core.mail.send_mail(data['subject'], data['body'].format(**options), data['from'], recipient)
