from django.conf.urls import patterns, include, url

from auth.decorators import require_login
import auth.views
import jupicp.views
import discourse.views

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^$', require_login(jupicp.views.DashboardView.as_view()), name='dashboard'),
    url(r'^login/', auth.views.LoginView.as_view(), name="login"),
    url(r'^logout/', auth.views.LogoutView.as_view(), name="logout"),
    url(r'^password/done/', jupicp.views.PasswordDoneView.as_view(), name="password_done"),
    url(r'^password/', jupicp.views.PasswordView.as_view(), name="password"),
    url(r'^register/done/', jupicp.views.RegisterDoneView.as_view(), name="register_done"),
    url(r'^register/', jupicp.views.RegisterView.as_view(), name="register"),

    url(r'^lists/', jupicp.views.MailinglistsListView.as_view(), name="lists"),

    url(r'^mails/add', require_login(jupicp.views.MailAddView.as_view()), name="mails_add"),
    url(r'^mails/verify/(?P<data_signed>[^/]+)', jupicp.views.MailVerifyView.as_view(), name="mails_verify"),
    url(r'^mails/(?P<mail>[^/]+)/del', require_login(jupicp.views.MailDelView.as_view()), name="mails_del"),
    url(r'^mails/(?P<mail>[^/]+)/verify', require_login(jupicp.views.MailVerifySendView.as_view()), name="mails_verify_send"),
    url(r'^mails/(?P<mail>[^/]+)/set_primary', require_login(jupicp.views.MailSetPrimaryView.as_view()), name="mails_set_primary"),

    url(r'^membership/connect/', require_login(jupicp.views.ConnectMembershipView.as_view()), name="membership_connect"),
    url(r'^membership/join/', require_login(jupicp.views.JoinMembershipView.as_view()), name="membership_join"),
    url(r'^membership/', require_login(jupicp.views.MembershipView.as_view()), name="membership"),
    url(r'^profile/done/', require_login(jupicp.views.ProfileView.as_view(done=True)), name="profile_done"),
    url(r'^profile/', require_login(jupicp.views.ProfileView.as_view()), name="profile"),

    url(r'^groups/create', jupicp.views.GroupsCreateView.as_view(), name="groups_create"),
    url(r'^groups/(?P<group_name>[^/]+)/members/add', require_login(jupicp.views.GroupsMemberAddView.as_view()), name="groups_member_add"),
    url(r'^groups/(?P<group_name>[^/]+)/members/(?P<user_name>[^/]+)/add', require_login(jupicp.views.GroupsMemberAddView.as_view()), name="groups_member_add"),
    url(r'^groups/(?P<group_name>[^/]+)/members/(?P<user_name>[^/]+)/del', require_login(jupicp.views.GroupsMemberDelView.as_view()), name="groups_member_del"),
    url(r'^groups/(?P<group_name>[^/]+)/managers/(?P<user_name>[^/]+)/add', require_login(jupicp.views.GroupsManagerAddView.as_view()), name="groups_manager_add"),
    url(r'^groups/(?P<group_name>[^/]+)/managers/(?P<user_name>[^/]+)/del', require_login(jupicp.views.GroupsManagerDelView.as_view()), name="groups_manager_del"),
    url(r'^groups/(?P<group_name>[^/]+)/delete', require_login(jupicp.views.GroupsDeleteView.as_view()), name="groups_delete"),
    url(r'^groups/(?P<group_name>[^/]+)', jupicp.views.GroupsDetailView.as_view(), name="groups_detail"),
    url(r'^groups/', jupicp.views.GroupsListView.as_view(), name="groups"),

    url(r'sso/discourse', require_login(discourse.views.DiscourseSSO.as_view()), name="sso_discourse"),

    url(r'json/groups/(?P<group_name>[^/]+)', jupicp.views.GroupsDetailJSONView.as_view()),
    url(r'json/checkUser', jupicp.views.CheckUserJSONView.as_view()),
)
