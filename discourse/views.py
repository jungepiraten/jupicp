from django.conf import settings
from discourse import utils

import urllib

class DiscourseSSO(RedirectView):
    permanent = False

    def get_redirect_url(self):
        if not utils.verify_sig(payload, sig, settings.DISCOURSE_SECRET):
            raise Http500("Signature invalid")
        request = utils.unpack_payload(payload)

        credentials = {
            "external_id": "ucp:{}".format(self.request.user.name),
            "nonce": request["nonce"],
            "username": self.request.user.name,
            "name": self.request.user.display_name,
            "email": self.request.user.primary_mail,
        }
        response = utils.pack_payload(credentials)

        response_sig = utils.calculate_sig(response, settings.DISCOURSE_SECRET)
        return "{}?{}".format(settings.DISCOURSE_LOGINURL, urllib.urlencode({"sso": response, "sig": response_sig}))
