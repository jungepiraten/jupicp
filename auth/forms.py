from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _


class LoginForm(forms.Form):
    user = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super(LoginForm, self).clean()
        try:
            ldap_user = settings.DIRECTORY.get_user(cleaned_data["user"])
            if not ldap_user.check_password(cleaned_data["password"]):
                raise AttributeError("wrong password")
        except AttributeError:
            raise forms.ValidationError(_("Wrong Username or Password"))
        cleaned_data['ldap_user'] = ldap_user
        return cleaned_data
