from django import forms
from django.conf import settings
from django.core import validators
from django.utils.translation import ugettext_lazy as _

import recaptcha_form.forms

class ProfileForm(forms.Form):
	current_password = forms.CharField(label=_("Current password"), widget=forms.PasswordInput)
	display_name = forms.CharField(label=_("Display name"))
	new_password = forms.CharField(label=_("New password"), widget=forms.PasswordInput, required=False)
	confirm_password = forms.CharField(label=_("Confirm new password"), widget=forms.PasswordInput, required=False)

	def __init__(self, user, **kwargs):
		super(ProfileForm, self).__init__(**kwargs)
		self.user = user
		
	def clean_current_password(self):
		password = self.cleaned_data["current_password"]
		if not self.user.check_password(password):
			raise forms.ValidationError(_("Wrong Password"))
		return password

	def clean_confim_password(self):
		if self.cleaned_data["new_password"] != self.cleaned_data["confirm_password"]:
			raise forms.ValidationError(_("Passwords do not match"))
		return self.cleaned_data["confirm_password"]

class RegisterForm(recaptcha_form.forms.RecaptchaForm):
	user = forms.CharField(validators=[validators.RegexValidator("^[-a-zA-Z0-9\\.]{3,25}$")] + [validators.RegexValidator(v) for v in settings.JUPICP_USERBLACKLIST], help_text=_("three to 25 characters. may only consist of letters, digits, hypens and dots"))
	mail = forms.EmailField()

	def clean_user(self):
		# Check if username is already in use
		user_name = self.cleaned_data['user']
		try:
			settings.DIRECTORY.get_user(user_name)
			raise forms.ValidationError(_("User already exists"))
		except AttributeError as e:
			pass
		return user_name

	def clean_mail(self):
		# Check if mail is already in use
		mail = self.cleaned_data['mail']
		try:
			settings.DIRECTORY.get_user_by_mail(mail)
			raise forms.ValidationError(_("Mail already used"))
		except AttributeError as e:
			pass
		return mail

class PasswordForm(forms.Form):
	user = forms.CharField(required=False)
	mail = forms.EmailField(required=False)

	def clean(self):
		user = self.cleaned_data.get('user')
		mail = self.cleaned_data.get('mail')
		
		try:
			if user:
				self.cleaned_data["user_object"] = settings.DIRECTORY.get_user(user)
			elif mail:
				self.cleaned_data["user_object"] = settings.DIRECTORY.get_user_by_mail(mail)
		except AttributeError:
			raise forms.ValidationError(_("User not found"))
		
		return super(PasswordForm, self).clean()

class GroupsCreateForm(forms.Form):
	display_name = forms.CharField(label=_("Name"))
	description = forms.CharField(widget=forms.Textarea, label=_("Description"))

class JoinMembershipForm(forms.Form):
	pass

class ConnectMembershipForm(forms.Form):
	pass
