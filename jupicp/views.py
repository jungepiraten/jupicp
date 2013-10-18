from django.conf import settings
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView, RedirectView
from django.views.generic.edit import FormView
from django.http import HttpResponseRedirect
from django.core import signing
from django.core.urlresolvers import reverse_lazy

import mailman
from jupicp import forms, utils

class RegisterView(FormView):
	template_name = "jupicp/register.html"
	form_class = forms.RegisterForm
	success_url = reverse_lazy("register_done")
	
	def form_valid(self, form):
		username = str(form.cleaned_data["user"])
		password = utils.generate_password()
		settings.DIRECTORY.create_user(username, password, username + "@community.junge-piraten.de", str(form.cleaned_data["mail"]))

		utils.send_mail(settings.JUPICP_REGISTERMAIL, {'username': username, 'password': password}, str(form.cleaned_data["mail"]))
		return super(RegisterView, self).form_valid(form)

class RegisterDoneView(TemplateView):
	template_name = "jupicp/register_done.html"

class DashboardView(TemplateView):
	template_name = "jupicp/dashboard.html"

class MembershipView(TemplateView):
	def get_template_names(self):
		if self.request.user.member_id:
			return "jupicp/membership.html"
		else:
			return "jupicp/membership_empty.html"

class JoinMembershipView(FormView):
	template_name = "jupicp/membership_join.html"
	form_class = forms.JoinMembershipForm

class ConnectMembershipView(FormView):
	template_name = "jupicp/membership_connect.html"
	form_class = forms.ConnectMembershipForm

class MailinglistsListView(TemplateView):
	template_name = "jupicp/lists.html"

	def post(self, request, **kwargs):
		for listname, mlist in mailman.get_lists(only_public=True, lock=False):
			subscribe = set()
			if "subscription_" + listname in self.request.POST and self.request.POST["subscription_" + listname]:
				subscribe.add(self.request.POST["subscription_" + listname])
			mails = [mail["mail"] for mail in self.request.user.get_mails(only_verified=True)]
			subscribed = set(mlist.members) & set(mails)
			
			members_remove = subscribed-subscribe
			members_add = subscribe-subscribed
			
			if len(members_remove | members_add) >0:
				mlist.Lock()
				for member in members_remove:
					mlist.ApprovedDeleteMember(member, whence="JuPiCP", admin_notif=False, userack=False)
				for member in subscribe-subscribed:
					mlist.ApprovedAddMember(mailman.UserDesc(address=member), admin_notif=False, ack=False)
				mlist.Save()
				mlist.Unlock()
			
		return HttpResponseRedirect(reverse_lazy("lists"))
	
	def get_context_data(self, **kwargs):
		context = super(MailinglistsListView, self).get_context_data(**kwargs)
		context['lists'] = mailman.get_lists(only_public=True, lock=False)
		context['mails'] = self.request.user.get_mails(only_verified=True)
		return context

class ProfileView(FormView):
	done = False
	template_name = "jupicp/profile.html"
	form_class = forms.ProfileForm
	success_url = reverse_lazy("profile_done")

	def get_initial(self):
		return {"display_name": self.request.user.display_name}

	def get_context_data(self, *args, **kwargs):
		context = super(ProfileView, self).get_context_data(*args, **kwargs)
		context['is_done'] = self.done
		return context

	def get_form_kwargs(self):
		kwargs = super(ProfileView, self).get_form_kwargs()
		kwargs['user'] = self.request.user
		return kwargs

	def form_valid(self, form):
		if form.cleaned_data["new_password"]:
			self.request.user.set_password(form.cleaned_data["new_password"])
		self.request.user.set_display_name(form.cleaned_data["display_name"])
		return super(ProfileView, self).form_valid(form)

class MailAddView(RedirectView):
	permanent = False

	def get_redirect_url(self, mail=None):
		if mail == None:
			mail = self.request.POST['mail']
		if not mail:
			return reverse_lazy("dashboard")
		
		# Check if mailadress is already in use
		try:
			settings.DIRECTORY.get_user_by_mail(mail)
			return reverse_lazy("dashboard")
		except:
			pass
		
		self.request.user.add_external_mail(mail)
		return reverse_lazy("mails_verify_send", str(mail))

class MailDelView(RedirectView):
	permanent = False

	def get_redirect_url(self, mail):
		self.request.user.del_external_mail(mail)
		return reverse_lazy("dashboard")

class MailVerifySendView(RedirectView):
	permanent = False

	def get_redirect_url(self, mail):
		token = signing.dumps([mail, self.request.user.name])
		token_link = self.request.build_absolute_uri(str(reverse_lazy("mails_verify", kwargs={"data_signed":token})))
		
		utils.send_mail(settings.JUPICP_VERIFYMAIL, {'username': self.request.user.name, 'mail': mail, 'token': token, 'token_link': token_link}, mail)
		return reverse_lazy("dashboard")

class MailVerifyView(TemplateView):
	template_name = "jupicp/mails_verify.html"
	
	def get_context_data(self, data_signed, **kwargs):
		context = super(MailVerifyView, self).get_context_data(**kwargs)
		mail, user_name = signing.loads(data_signed)
		user = settings.DIRECTORY.get_user(user_name)
		user.verify_external_mail(mail)
		
		context["mail"] = mail
		context["user"] = user
		return context

class PasswordView(FormView):
	template_name = "jupicp/password.html"
	form_class = forms.PasswordForm
	success_url = reverse_lazy("password_done")
	
	def form_valid(self, form):
		user = form.cleaned_data['user_object']
		password = utils.generate_password()
		
		user.set_password(password)
		utils.send_mail(settings.JUPICP_PASSWORDMAIL, {'username': user.name, 'mail': user.mail, 'password': password}, [mail["mail"] for mail in user.external_mails] + [user.mail])
		return super(PasswordView, self).form_valid(form)

class PasswordDoneView(TemplateView):
	template_name = "jupicp/password_done.html"

class GroupsListView(TemplateView):
	template_name = "jupicp/groups.html"

	def get_context_data(self, **kwargs):
		context = super(GroupsListView, self).get_context_data(**kwargs)
		context['groups'] = settings.DIRECTORY.get_groups()
		context['may_create'] = self.request.user.match_dn(settings.ADMIN_DN)
		return context

class GroupsCreateView(FormView):
	template_name = "jupicp/groups_create.html"
	form_class = forms.GroupsCreateForm
	
	def form_valid(self):
		name = settings.DIRECTORY.create_group()
		return HttpResponseRedirect(reverse_lazy("groups_detail", kwargs={"group_name": name}))

class GroupsDetailView(TemplateView):
	template_name = "jupicp/groups_detail.html"

	def get_context_data(self, **kwargs):
		context = super(GroupsDetailView, self).get_context_data(**kwargs)
		context['group'] = settings.DIRECTORY.get_group(kwargs["group_name"])
		if self.request.user:
			context['is_member'] = context['group'].is_member(self.request.user)
			context['may_join'] = context['group'].may_join(self.request.user)
			context['may_edit'] = context['group'].may_edit(self.request.user)
		return context

class GroupsMemberAddView(RedirectView):
	permanent = False

	def get_redirect_url(self, group_name, user_name=None):
		group = settings.DIRECTORY.get_group(group_name)
		if not user_name:
			user_name = self.request.POST["user"]
		user = settings.DIRECTORY.get_user(user_name)

		if (not group.may_edit(self.request.user)) and (self.request.user == user and not group.may_join(self.request.user)):
			raise Exception("403")
		group.add_member(user)
		
		return reverse_lazy("groups_detail", kwargs={'group_name':group_name})

class GroupsMemberDelView(RedirectView):
	permanent = False
	
	def get_redirect_url(self, group_name, user_name):
		group = settings.DIRECTORY.get_group(group_name)
		user = settings.DIRECTORY.get_user(user_name)

		if (not group.may_edit(self.request.user)) and (self.request.user == user and not group.is_member(self.request.user)):
			raise Exception("403")
		group.del_member(user)

		return reverse_lazy("groups_detail", kwargs={'group_name':group_name})
