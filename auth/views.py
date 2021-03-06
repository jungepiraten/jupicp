from django.views.generic.base import RedirectView
from django.core.urlresolvers import reverse_lazy
from django.views.generic.edit import FormView

from auth import forms


class LoginView(FormView):
    template_name = "auth/login.html"
    form_class = forms.LoginForm

    def get_success_url(self):
        if "redirect" in self.request.GET:
            return self.request.GET["redirect"]
        return reverse_lazy("dashboard")

    def form_valid(self, form):
        self.request.session["user"] = form.cleaned_data["ldap_user"].name
        return super(LoginView, self).form_valid(form)


class LogoutView(RedirectView):
    permanent = False

    def get_redirect_url(self):
        if "user" in self.request.session:
            del(self.request.session["user"])
        return reverse_lazy("login")
