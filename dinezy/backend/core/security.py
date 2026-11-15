import hashlib
import ipaddress
import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger('core.security')

CDN = 'https://cdn.jsdelivr.net https://cdnjs.cloudflare.com'
CSP = '; '.join([
    "default-src 'self'",
    f"script-src 'self' 'unsafe-inline' {CDN}",
    f"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com {CDN}",
    f"font-src 'self' data: https://fonts.gstatic.com {CDN}",
    "img-src 'self' data: blob:",
    f"connect-src 'self' {CDN}",
    "frame-src 'self' blob:",
    "frame-ancestors 'self'",
    "form-action 'self'",
    "base-uri 'self'",
    "object-src 'none'",
])
PERMISSIONS = 'camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()'


def client_ip(request):
    remote = request.META.get('REMOTE_ADDR', '')
    if getattr(settings, 'DINEZY_TRUST_PROXY', False):
        fwd = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if fwd:
            remote = fwd.split(',')[0].strip()
    try:
        return str(ipaddress.ip_address(remote))
    except ValueError:
        return '0.0.0.0'


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault('Content-Security-Policy', CSP)
        response.setdefault('Permissions-Policy', PERMISSIONS)
        response.setdefault('X-Content-Type-Options', 'nosniff')
        response.setdefault('Cross-Origin-Resource-Policy', 'same-origin')
        if request.path.startswith(('/panel/', '/admin/', '/login/', '/daftar/')) or '/owner/' in request.path \
                or '/kasir/' in request.path:
            response.setdefault('Cache-Control', 'no-store, private')
        return response


class LoginGuard:

    def __init__(self, request, username):
        self.ip = client_ip(request)
        user = hashlib.sha256((username or '').lower().encode()).hexdigest()[:24]
        self.k_user = f'dz:login:u:{self.ip}:{user}'
        self.k_ip = f'dz:login:ip:{self.ip}'
        self.batas_user = int(getattr(settings, 'DINEZY_LOGIN_MAKS_GAGAL', 5))
        self.batas_ip = self.batas_user * 4
        self.durasi = int(getattr(settings, 'DINEZY_LOGIN_KUNCI_MENIT', 15)) * 60

    def terkunci(self):
        return (cache.get(self.k_user, 0) >= self.batas_user) or (cache.get(self.k_ip, 0) >= self.batas_ip)

    def gagal(self, username):
        for key in (self.k_user, self.k_ip):
            cache.add(key, 0, self.durasi)
            try:
                cache.incr(key)
            except ValueError:
                cache.set(key, 1, self.durasi)
        logger.warning('Login gagal: user=%r ip=%s', (username or '')[:40], self.ip)

    def berhasil(self):
        cache.delete(self.k_user)

    @property
    def menit(self):
        return self.durasi // 60


def batas_permintaan(request, nama, maks, detik):
    key = f'dz:rl:{nama}:{client_ip(request)}'
    cache.add(key, 0, detik)
    try:
        jumlah = cache.incr(key)
    except ValueError:
        cache.set(key, 1, detik)
        jumlah = 1
    if jumlah > maks:
        logger.warning('Batas permintaan %s terlampaui: ip=%s', nama, client_ip(request))
        return False
    return True


def admin_login_redirect(request):
    from django.shortcuts import redirect
    from django.utils.http import url_has_allowed_host_and_scheme
    from urllib.parse import urlencode
    nxt = request.GET.get('next', '')
    q = {'mode': 'admin'}
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        q['next'] = nxt
    return redirect('/login/?' + urlencode(q))
