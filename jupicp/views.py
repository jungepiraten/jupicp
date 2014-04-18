from django.conf import settings
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, RedirectView
from django.views.generic.edit import FormView
from django.core import signing
from django.core.urlresolvers import reverse_lazy
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.utils.datastructures import MultiValueDictKeyError

import mailman
from jupicp import forms, utils

@utils.classview_decorator(csrf_exempt)
class CheckUserJSONView(utils.JSONView):
	def post(self, *args, **kwargs):
		try:
			ldap_user = settings.DIRECTORY.get_user(self.request.POST["user"])
			if not ldap_user.check_password(self.request.POST["password"]):
				return {"status": "fail", "message": "Authentification failed"}
			return {
				"status": "success",
				"name": ldap_user.name,
				"displayName": ldap_user.display_name,
				"groups": [group.name for group in ldap_user.get_groups()],
			}
		except MultiValueDictKeyError:
			return {"status": "fail", "message": "Need parameters user and password via POST"}
		except AttributeError:
			return {"status": "fail", "message": "Authentification failed"}

class RegisterView(FormView):
	template_name = "jupicp/register.html"
	form_class = forms.RegisterForm
	success_url = reverse_lazy("register_done")
	
	def form_valid(self, form):
		username = form.cleaned_data["user"]
		password = utils.generate_password()
		settings.DIRECTORY.create_user(username, password, form.cleaned_data["mail"])

		utils.send_mail(settings.JUPICP_REGISTERMAIL, {'username': username, 'password': password}, form.cleaned_data["mail"])
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
		lists = {}
		for listname, mlist in mailman.get_lists(only_public=True, lock=False):
			if mlist.host_name not in lists:
				lists[mlist.host_name] = {}
			lists[mlist.host_name][listname] = mlist
		context['lists'] = lists
		if self.request.user:
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
		return reverse_lazy("mails_verify_send", kwargs={'mail': mail})

class MailDelView(RedirectView):
	permanent = False

	def get_redirect_url(self, mail):
		self.request.user.del_external_mail(mail)
		return reverse_lazy("dashboard")

class MailVerifySendView(RedirectView):
	permanent = False

	def get_redirect_url(self, mail):
		token = signing.dumps([mail, self.request.user.name])
		token_link = self.request.build_absolute_uri(reverse_lazy("mails_verify", kwargs={"data_signed":token}))
		
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
		mails = [mail["mail"] for mail in user.external_mails]
		if user.mail:
			mails.append(user.mail)
		utils.send_mail(settings.JUPICP_PASSWORDMAIL, {'username': user.name, 'mail': user.mail, 'password': password}, mails)
		return super(PasswordView, self).form_valid(form)

class PasswordDoneView(TemplateView):
	template_name = "jupicp/password_done.html"

class GroupsListView(TemplateView):
	template_name = "jupicp/groups.html"

	def get_context_data(self, **kwargs):
		context = super(GroupsListView, self).get_context_data(**kwargs)
		context['groups'] = settings.DIRECTORY.get_groups()
		if self.request.user:
			context['may_create'] = self.request.user.match_dn(settings.ADMIN_DN)
		return context

class GroupsCreateView(FormView):
	template_name = "jupicp/groups_create.html"
	form_class = forms.GroupsCreateForm
	
	def form_valid(self, form):
		if not self.request.user.match_dn(settings.ADMIN_DN):
			raise PermissionDenied
		group = settings.DIRECTORY.create_group(form.cleaned_data["display_name"], form.cleaned_data["description"], [ self.request.user ])
		return HttpResponseRedirect(reverse_lazy("groups_detail", kwargs={"group_name": group.name}))

@utils.classview_decorator(utils.raise_404)
class GroupsDetailView(TemplateView):
	template_name = "jupicp/groups_detail.html"

	def get_context_data(self, **kwargs):
		context = super(GroupsDetailView, self).get_context_data(**kwargs)
		try:
			context['group'] = settings.DIRECTORY.get_group(kwargs["group_name"])
		except:
			raise ObjectDoesNotExist
		if self.request.user:
			context['is_member'] = context['group'].is_member(self.request.user)
			context['may_join'] = context['group'].may_join(self.request.user)
			context['may_edit'] = context['group'].may_edit(self.request.user)
		return context

@utils.classview_decorator(utils.raise_404)
class GroupsDetailJSONView(utils.JSONView):
	def get(self, *args, **kwargs):
		try:
			group = settings.DIRECTORY.get_group(kwargs["group_name"])
		except:
			raise ObjectDoesNotExist
		return {"id": group.name, "name": group.display_name, "description": group.description, "members": [user.name for user in group.get_members()]}

@utils.classview_decorator(utils.raise_404)
class GroupsDeleteView(RedirectView):
	permanent = False

	def get_redirect_url(self, group_name):
		try:
			group = settings.DIRECTORY.get_group(group_name)
		except:
			raise ObjectDoesNotExist

		if not group.may_edit(self.request.user):
			raise PermissionDenied
		group.delete()

		return reverse_lazy("groups")

@utils.classview_decorator(utils.raise_404)
class GroupsMemberAddView(RedirectView):
	permanent = False

	def get_redirect_url(self, group_name, user_name=None):
		try:
			group = settings.DIRECTORY.get_group(group_name)
			if not user_name:
				user_name = self.request.POST["user"]
			user = settings.DIRECTORY.get_user(user_name)
		except:
			raise ObjectDoesNotExist

		if (not group.may_edit(self.request.user)) and (self.request.user == user and not group.may_join(self.request.user)):
			raise PermissionDenied
		group.add_member(user)
		
		return reverse_lazy("groups_detail", kwargs={'group_name':group_name})

@utils.classview_decorator(utils.raise_404)
class GroupsMemberDelView(RedirectView):
	permanent = False
	
	def get_redirect_url(self, group_name, user_name):
		try:
			group = settings.DIRECTORY.get_group(group_name)
			user = settings.DIRECTORY.get_user(user_name)
		except:
			raise ObjectDoesNotExist

		if (not group.may_edit(self.request.user)) and (self.request.user == user and not group.is_member(self.request.user)):
			raise PermissionDenied
		group.del_member(user)

		return reverse_lazy("groups_detail", kwargs={'group_name':group_name})
