# -*- coding: utf-8 -*-

import ldap
import ldap.modlist

# LDAP does not accept empty groups. Use this string to have non-empty groups. Must not be a valid user-dn
EMPTY_LIST_IDENTIFIER = "cn=empty"

# fake-dn to identify all users. Must not be a valid user-dn
EVERYBODY_IDENTIFIER = "cn=everybody"

# fake-dn to identify guests. Must not be a valid user-dn
ANONYMOUS_IDENTIFIER = "cn=anonymous"

class Directory:
    def __init__(self, ldap_host='', bind_user='', bind_password='', user_dn_base='', group_dn_base=''):
        def get_connection():
            conn = ldap.initialize(ldap_host)
            conn.simple_bind_s(bind_user, bind_password)
            return conn

        self.generate_connection = get_connection

        self.user_dn_base = user_dn_base
        self.group_dn_base = group_dn_base

    def get_user_dn(self, uid):
        return "uid={name},{base_dn}".format(name=uid, base_dn=self.user_dn_base)

    def get_user(self, uid):
        return self.get_user_by_dn(self.get_user_dn(uid))

    def get_user_by_mail(self, mail):
        conn = self.generate_connection()
        res = conn.search_s(self.user_dn_base, ldap.SCOPE_ONELEVEL, "(|(mail={0})(email={0})(otherMailbox={0}))".format(mail))
        if len(res) != 1:
            raise AttributeError("No such object".format(mail))
        dn, user = res[0]
        return self.get_user_by_dn(dn)

    def get_user_by_dn(self, dn):
        return User(self, dn)

    def create_user(self, uid, password, externalMail):
        conn = self.generate_connection()
        conn.add_s(self.get_user_dn(uid), ldap.modlist.addModlist({
            'objectClass': ["inetOrgPerson", "extensibleObject"],
            'cn': uid.encode("utf-8"),
            'otherMailbox': externalMail.encode("utf-8"),
            'userPassword': password.encode("utf-8"),
            'sn': "-",
        }))
        return self.get_user(uid)

    def get_group_dn(self, group):
        return "cn={name},{base_dn}".format(name=group, base_dn=self.group_dn_base)

    def get_groups(self):
        conn = self.generate_connection()
        return [self.get_group(attrs["cn"][0]) for dn, attrs in conn.search_s(self.group_dn_base, ldap.SCOPE_ONELEVEL, "cn=*", ["cn"])]

    def get_group(self, group):
        return self.get_group_by_dn(self.get_group_dn(group))

    def get_group_by_dn(self, dn):
        return Group(self, dn)

    def create_group(self, display_name, description, members, managers=[], owners=[]):
        group = display_name.lower().replace("/", "-").replace(" ", "_")

        conn = self.generate_connection()
        conn.add_s(self.get_group_dn(group), ldap.modlist.addModlist({
            'objectClass': ["groupOfUniqueNames", "extensibleObject"],
            'cn': group.encode("utf-8"),
            'displayName': display_name.encode("utf-8"),
            'description': description.encode("utf-8"),
            'owner': [owner.dn for owner in owners],
            'manager': [manager.dn for manager in managers] if managers != [] else [member.dn for member in members],
            'uniqueMember': [member.dn for member in members]
        }))
        return self.get_group(group)


class DirectoryResult:
    dn = ''

    def __init__(self, directory, dn):
        self.directory = directory
        self.dn = dn

        conn = self.directory.generate_connection()
        try:
            result = conn.search_s(self.dn, ldap.SCOPE_BASE)
        except ldap.NO_SUCH_OBJECT:
            raise AttributeError("No such object".format(dn))
        dn, attrs = result[0]
        self.attrs = attrs
        self.fill_attrs(attrs)


class User(DirectoryResult):
    def fill_attrs(self, attrs):
        self.name = attrs["uid"][0]
        self.display_name = attrs["cn"][0] if "cn" in attrs else attrs["uid"][0]
        self.mail = None
        self.primary_mail = None
        self.external_mails = []
        if "otherMailbox" in attrs:
            self.external_mails = self.external_mails + [{"verified": False, "mail": mail} for mail in attrs["otherMailbox"]]
        if "email" in attrs:
            self.primary_mail = attrs["email"][0]
            self.external_mails = self.external_mails + [{"verified": True, "mail": mail} for mail in attrs["email"]]
        if "mail" in attrs:
            self.primary_mail = attrs["mail"][0]
            self.mail = attrs["mail"][0]
        self.given_name = attrs["givenName"][0] if "givenName" in attrs else ""
        self.surname = attrs["sn"][0] if attrs["sn"][0] != "-" else ""
        self.common_name = attrs["cn"][0]
        self.member_id = attrs["employeeNumber"][0] if "employeeNumber" in attrs else None

    def check_password(self, password):
        conn = self.directory.generate_connection()
        try:
            conn.simple_bind_s(self.dn, password)
            return True
        except ldap.INVALID_CREDENTIALS:
            return False

    def get_mails(self, only_verified=False):
        if only_verified:
            return [m for m in self.get_mails() if m["verified"]]

        if self.mail:
            return self.external_mails + [{"verified": True, "mail": self.mail}]
        else:
            return self.external_mails

    def set_password(self, password):
        conn = self.directory.generate_connection()
        conn.passwd_s(self.dn, None, password)

    def set_names(self, given_name, surname, common_name):
        conn = self.directory.generate_connection()
        conn.modify_s(self.dn, ldap.modlist.modifyModlist({
            "givenName": self.attrs["givenName"] if "givenName" in self.attrs else [],
            "sn": self.attrs["sn"] if "sn" in self.attrs else [],
            "cn": self.attrs["cn"] if "cn" in self.attrs else []
        }, {
            "givenName": given_name.encode("utf-8") if given_name != "" else [],
            "sn": surname.encode("utf-8") if surname != "" else ["-"],
            "cn": common_name.encode("utf-8")
        }))
        self.attrs["givenName"] = [given_name]
        self.given_name = given_name
        self.attrs["sn"] = [surname if surname != "" else "-"]
        self.surname = surname
        self.attrs["cn"] = [common_name]
        self.common_name = common_name

    def set_external_mails(self, external_mails):
        conn = self.directory.generate_connection()
        # Add test-item to cause a "real" change, even if there was just reordering
        conn.modify_s(self.dn, ldap.modlist.modifyModlist({
            "otherMailbox": [m['mail'] for m in self.external_mails if not m['verified']],
            "emailAddress": [m['mail'] for m in self.external_mails if m['verified']]
        }, {
            "otherMailbox": [m['mail'] for m in external_mails if not m['verified']] + ["_TOBEREMOVED"],
            "emailAddress": [m['mail'] for m in external_mails if m['verified']] + ["_TOBEREMOVED"]
        }))
        conn.modify_s(self.dn, ldap.modlist.modifyModlist({
            "otherMailbox": [m['mail'] for m in external_mails if not m['verified']] + ["_TOBEREMOVED"],
            "emailAddress": [m['mail'] for m in external_mails if m['verified']] + ["_TOBEREMOVED"]
        }, {
            "otherMailbox": [m['mail'] for m in external_mails if not m['verified']],
            "emailAddress": [m['mail'] for m in external_mails if m['verified']]
        }))
        self.external_mails = external_mails

    def set_primary_mail(self, primary_mail):
        self.set_external_mails([m for m in self.external_mails if m['mail'] == primary_mail] + [m for m in self.external_mails if m['mail'] != primary_mail])

    def verify_external_mail(self, external_mail):
        external_mails = []
        for m_ in self.external_mails:
            # Avoid to do the change now since set_external_mails will need the old list to generate diff
            m = m_.copy()
            if m['mail'] == external_mail:
                m['verified'] = True
            external_mails.append(m)
        self.set_external_mails(external_mails)

    def add_external_mail(self, external_mail):
        self.set_external_mails(self.external_mails + [{"verified": False, "mail": external_mail.encode("utf-8")}])

    def del_external_mail(self, external_mail):
        self.set_external_mails([m for m in self.external_mails if m['mail'] != external_mail])

    def get_group_dns(self):
        conn = self.directory.generate_connection()
        return [dn.lower() for dn, attrs in conn.search_s(self.directory.group_dn_base, ldap.SCOPE_ONELEVEL, "uniqueMember={0}".format(self.dn), ["cn"])]

    def get_groups(self):
        return [self.directory.get_group_by_dn(group_dn) for group_dn in self.get_group_dns()]

    """
    Check if we are specified by some dn. This may either be the case it is our dn or if the dn specifies a group we are part of
    """
    def match_dn(self, dn):
        if dn.lower() == EVERYBODY_IDENTIFIER:
            return True
        if dn.lower() == self.dn.lower():
            return True
        if dn.lower() in self.get_group_dns():
            return True
        return False


class Group(DirectoryResult):
    dn = ''
    name = ''
    description = ''
    mail = ''
    members = []
    owners = []
    managers = []
    secretary = []

    def fill_attrs(self, attrs):
        self.name = attrs["cn"][0]
        self.mail = attrs["mail"][0] if "mail" in attrs else None
        self.display_name = attrs["displayName"][0] if "displayName" in attrs else attrs["cn"][0]
        self.description = attrs["description"][0] if "description" in attrs else ''
        # Keep track what's really in the list to generate valid LDIFs later
        self._members = attrs["uniqueMember"]
        self.members = [member for member in self._members if member != EMPTY_LIST_IDENTIFIER]
        self.owners = attrs["owner"] if "owner" in attrs else []
        self.managers = attrs["manager"] if "manager" in attrs else []
        self.secretary = attrs["secretary"] if "secretary" in attrs else [ANONYMOUS_IDENTIFIER, EVERYBODY_IDENTIFIER]

    def set_owners(self, owners):
        conn = self.directory.generate_connection()
        conn.modify_s(self.dn, ldap.modlist.modifyModlist({
            'owners': self.owners
        }, {
            'owners': owners
        }))
        self.owners = owners

    def is_member(self, user):
        return user.dn in self.members

    def get_members(self):
        return [self.directory.get_user_by_dn(member) for member in self.members]

    def set_members(self, members):
        if not members:
            members = [EMPTY_LIST_IDENTIFIER]

        conn = self.directory.generate_connection()
        conn.modify_s(self.dn, ldap.modlist.modifyModlist({
            'uniqueMember': self._members
        }, {
            'uniqueMember': members
        }))
        self.members = members

    def add_member(self, user):
        self.set_members(self.members + [user.dn.encode("utf-8")])
        # If this user was invited indivually, this is not longer needed now
        if user.dn in self.owners:
            self.set_owners([owner for owner in self.owners if owner.lower() != user.dn.lower()])

    def del_member(self, user):
        self.set_members([member for member in self.members if member.lower() != user.dn.lower()])

    def set_managers(self, managers):
        conn = self.directory.generate_connection()
        conn.modify_s(self.dn, ldap.modlist.modifyModlist({
            'manager': self.managers
        }, {
            'manager': managers
        }))
        self.managers = managers

    def add_manager(self, user):
        self.set_managers(self.managers + [user.dn.encode("utf-8")])

    def del_manager(self, user):
        self.set_managers([manager for manager in self.managers if manager.lower() != user.dn.lower()])

    def delete(self):
        conn = self.directory.generate_connection()
        conn.delete_s(self.dn)

    def may_see(self, user):
        if user is None:
            return ANONYMOUS_IDENTIFIER in self.secretary
        for secretary in self.secretary:
            if user.match_dn(secretary):
                return True
        return False

    def may_edit(self, user):
        if user is None:
            return ANONYMOUS_IDENTIFIER in self.managers
        for manager in self.managers:
            if user.match_dn(manager):
                return True
        return False

    def may_join(self, user):
        if user is None:
            return ANONYMOUS_IDENTIFIER in self.owner
        for owner in self.owners:
            if user.match_dn(owner):
                return True
        return False
