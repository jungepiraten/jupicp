import sys
sys.path.append("/usr/lib/mailman/bin")
import paths
from Mailman import Errors
from Mailman.MailList import MailList
from Mailman import Utils


def get_listnames(only_public=False, **kwargs):
    names = Utils.list_names()
    names.sort()
    if only_public:
        names = [name for name in names if get_list(name, lock=False).subscribe_policy == 1]
    return names


def get_lists(**kwargs):
    return [(name, get_list(name, **kwargs)) for name in get_listnames(**kwargs)]


def get_list(name, lock=False, **kwargs):
    return MailList(name, lock=lock)


# Need that to give a correct structure to mailman
class UserDesc:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
