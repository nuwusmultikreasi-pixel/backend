import logging
import secrets
import string

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils.text import slugify

from .models import Tenant, UserProfile
from .secretbox import simpan_password

logger = logging.getLogger(__name__)

ROLES = (('owner', 'Owner'), ('kasir', 'Kasir'))


def unique_slug(nama_cafe):
    base = slugify(nama_cafe)[:40] or 'cafe'
    slug, i = base, 2
    while Tenant.objects.filter(slug__iexact=slug).exists():
        slug = f"{base}-{i}"
        i += 1
    return slug


def generate_password(length=10):
    alphabet = string.ascii_letters + string.digits
    while True:
        pwd = ''.join(secrets.choice(alphabet) for _ in range(length))
        if any(c.isdigit() for c in pwd) and any(c.isupper() for c in pwd) and any(c.islower() for c in pwd):
            return pwd


def _unique_username(role, slug):
    base = f"{role}.{slugify(slug) or 'cafe'}"[:140]
    username, i = base, 2
    while User.objects.filter(username__iexact=username).exists():
        username = f"{base}{i}"
        i += 1
    return username


@transaction.atomic
def ensure_cafe_accounts(tenant, reset_password=False):
    hasil = []
    for role, label in ROLES:
        profile = UserProfile.objects.filter(tenant=tenant, role=role).select_related('user').first()
        if profile:
            if not reset_password:
                continue
            user = profile.user
            password = generate_password()
            user.set_password(password)
            user.is_active = True
            user.save()
            simpan_password(user, password)
            hasil.append({'role': label, 'username': user.username, 'password': password, 'baru': False})
            continue

        password = generate_password()
        user = User.objects.create_user(
            username=_unique_username(role, tenant.slug),
            password=password,
            email=tenant.email_owner or '',
            first_name=((tenant.nama_owner if role == 'owner' else f"Kasir {tenant.nama_cafe}") or '')[:150],
        )
        UserProfile.objects.create(user=user, tenant=tenant, role=role)
        simpan_password(user, password)
        hasil.append({'role': label, 'username': user.username, 'password': password, 'baru': True})
    return hasil


def send_credentials_email(tenant, accounts, base_url=''):
    if not tenant.email_owner or not accounts:
        return False
    base_url = (base_url or '').rstrip('/')
    context = {
        'tenant': tenant,
        'accounts': accounts,
        'login_url': f"{base_url}/login/?cafe={tenant.slug}",
        'logo_url': f"{base_url}{settings.STATIC_URL if settings.STATIC_URL.startswith('/') else '/' + settings.STATIC_URL}core/img/dinezy-mark-white.png" if base_url else '',
    }
    subject = f"Akun Dinezy untuk {tenant.nama_cafe}"
    try:
        msg = EmailMultiAlternatives(
            subject,
            render_to_string('emails/credentials.txt', context),
            settings.DEFAULT_FROM_EMAIL,
            [tenant.email_owner],
        )
        msg.attach_alternative(render_to_string('emails/credentials.html', context), 'text/html')
        msg.send(fail_silently=False)
        return True
    except Exception as exc:
        logger.warning("Gagal mengirim email kredensial ke %s: %s", tenant.email_owner, exc)
        return False


USERNAME_RE = r'^[A-Za-z0-9._-]{4,30}$'


def validate_new_account(username, password, password2, label, user_for_similarity=None):
    import re
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError

    errors = []
    if not re.match(USERNAME_RE, username or ''):
        errors.append(f'Username {label} harus 4–30 karakter: huruf, angka, titik, minus, atau garis bawah (tanpa spasi).')
    elif User.objects.filter(username__iexact=username).exists():
        errors.append(f'Username {label} "{username}" sudah dipakai. Silakan pilih username lain.')
    if not password:
        errors.append(f'Password {label} wajib diisi.')
    elif password != password2:
        errors.append(f'Konfirmasi password {label} tidak sama.')
    else:
        try:
            validate_password(password, user=User(username=username or '', first_name=user_for_similarity or ''))
        except ValidationError as e:
            errors.extend(f'Password {label}: {m}' for m in e.messages)
    return errors


@transaction.atomic
def create_custom_accounts(tenant, owner_username, owner_password, kasir_username, kasir_password):
    hasil = []
    for role, label, username, password in (('owner', 'Owner', owner_username, owner_password),
                                            ('kasir', 'Kasir', kasir_username, kasir_password)):
        user = User.objects.create_user(
            username=username, password=password, email=tenant.email_owner or '',
            first_name=((tenant.nama_owner if role == 'owner' else f"Kasir {tenant.nama_cafe}") or '')[:150],
        )
        UserProfile.objects.create(user=user, tenant=tenant, role=role)
        simpan_password(user, password)
        hasil.append({'role': label, 'username': username, 'password': None, 'baru': True})
    return hasil
