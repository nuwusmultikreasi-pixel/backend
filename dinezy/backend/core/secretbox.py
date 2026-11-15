import base64, hashlib, hmac, os

from django.conf import settings

_VER = b'v1'


def _keys():
    base = hashlib.sha256(('dz-pw-box:' + settings.SECRET_KEY).encode()).digest()
    return (hmac.new(base, b'enc', hashlib.sha256).digest(), hmac.new(base, b'mac', hashlib.sha256).digest())


def _stream(key, nonce, n):
    out, i = b'', 0
    while len(out) < n:
        out += hmac.new(key, nonce + i.to_bytes(4, 'big'), hashlib.sha256).digest()
        i += 1
    return out[:n]


def encrypt(text):
    if not text:
        return ''
    ek, mk = _keys()
    data = text.encode('utf-8')
    nonce = os.urandom(16)
    ct = bytes(a ^ b for a, b in zip(data, _stream(ek, nonce, len(data)), strict=True))
    tag = hmac.new(mk, _VER + nonce + ct, hashlib.sha256).digest()[:16]
    return base64.urlsafe_b64encode(_VER + nonce + tag + ct).decode()


def decrypt(token):
    if not token:
        return None
    try:
        raw = base64.urlsafe_b64decode(token.encode())
        ver, nonce, tag, ct = raw[:2], raw[2:18], raw[18:34], raw[34:]
        if ver != _VER:
            return None
        ek, mk = _keys()
        if not hmac.compare_digest(tag, hmac.new(mk, ver + nonce + ct, hashlib.sha256).digest()[:16]):
            return None
        return bytes(a ^ b for a, b in zip(ct, _stream(ek, nonce, len(ct)), strict=True)).decode('utf-8')
    except Exception:
        return None


def simpan_password(user, password):
    from django.utils import timezone
    from .models import UserProfile
    if not password:
        return
    UserProfile.objects.filter(user=user).update(pw_enc=encrypt(password), pw_set_at=timezone.now())
