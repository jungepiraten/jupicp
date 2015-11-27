import urllib
from hashlib import sha256
import hmac
from base64 import b64decode, b64encode

def pack_payload(payload):
    return b64encode(urllib.urlencode(payload).encode())

def unpack_payload(payload):
    payload = b64decode(urllib.unquote(payload)).decode()
    return dict(nonce.split("=") for nonce in payload.split('&'))

def calculate_sig(payload, secret):
    return hmac.new(secret.encode(), payload, sha256).hexdigest()

def verify_sig(payload, sig, secret):
    payload = urllib.unquote(payload)
    computed_sig = hmac.new(secret.encode(), payload.encode(), sha256).hexdigest()
    return sig == computed_sig
