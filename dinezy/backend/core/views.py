import logging
import re
import secrets
from datetime import date

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError as DRFValidationError
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import BasePermission, SAFE_METHODS, IsAdminUser
from rest_framework.response import Response

from .secretbox import decrypt, simpan_password
from .models import Meja, Menu, Order, Tenant
from .serializers import (
    TenantSerializer,
    MenuSerializer,
    OrderSerializer,
    UploadBuktiSerializer,
    MejaSerializer,
)
from .utils import generate_pdf
from .accounts import create_custom_accounts, send_credentials_email, unique_slug, validate_new_account
from .pengumuman import IKON, banner_aktif, untuk_cafe
from .perjanjian import catat_persetujuan_sk
from .security import LoginGuard, batas_permintaan, client_ip
from .uploads import cek_gambar, ganti_file
from .billing import running_month, status_tagihan, sync_tenant, tarif

logger = logging.getLogger(__name__)


def get_profile(user):
    if not user or not user.is_authenticated:
        return None
    profile = getattr(user, 'profile', None)
    if profile and profile.tenant:
        return profile
    return None


def filter_by_tenant(request, queryset):
    profile = get_profile(request.user)
    if profile and not request.user.is_superuser:
        return queryset.filter(tenant=profile.tenant)

    tenant_id = request.query_params.get('tenant')
    tenant_slug = request.query_params.get('tenant_slug')
    if tenant_id:
        return queryset.filter(tenant_id=int(tenant_id)) if tenant_id.isdigit() else queryset.none()
    if tenant_slug:
        return queryset.filter(tenant__slug=tenant_slug[:60])
    return queryset


class IsStaffOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or bool(request.user and request.user.is_staff)


class MenuPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if request.user and request.user.is_superuser:
            return True
        profile = get_profile(request.user)
        if not profile:
            return False
        if getattr(view, 'action', None) == 'toggle_tersedia':
            return profile.role in ('owner', 'kasir')
        return profile.role == 'owner'

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS or request.user.is_superuser:
            return True
        profile = get_profile(request.user)
        return bool(profile and obj.tenant_id == profile.tenant_id)


class TenantUserWritePermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and (request.user.is_superuser or get_profile(request.user)))


class OrderPermission(BasePermission):
    PUBLIC_ACTIONS = ('create', 'retrieve', 'upload_bukti')

    def has_permission(self, request, view):
        if getattr(view, 'action', None) in self.PUBLIC_ACTIONS:
            return True
        return bool(request.user and (request.user.is_superuser or get_profile(request.user)))

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        profile = get_profile(request.user)
        if profile:
            return obj.tenant_id == profile.tenant_id
        token = request.headers.get('X-Order-Token') or request.query_params.get('token') or ''
        return bool(token) and secrets.compare_digest(token, obj.akses_token)


class TenantViewSet(viewsets.ModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    lookup_field = 'slug'
    permission_classes = [IsStaffOrReadOnly]

    @action(detail=True, methods=['get'], permission_classes=[IsAdminUser])
    def cetak_invoice(self, request, slug=None):
        tenant = self.get_object()

        bulan = request.query_params.get('bulan', 'Semua Periode')
        tahun = request.query_params.get('tahun', str(date.today().year))

        context = {
            'tenant': tenant,
            'bulan': bulan,
            'tahun': tahun,
            'tanggal_cetak': date.today().strftime("%d-%m-%Y")
        }

        pdf = generate_pdf('invoice_template.html', context)

        if pdf:
            response = HttpResponse(pdf, content_type='application/pdf')
            filename = f"Invoice_{tenant.slug}_{bulan}_{tahun}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        return Response({'error': 'Gagal membuat file PDF invoice.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def toggle_lock(self, request, slug=None):
        tenant = self.get_object()
        tenant.is_locked = not tenant.is_locked
        tenant.save()

        status_akses = "Terkunci" if tenant.is_locked else "Aktif"
        return Response({'message': f'Status akses {tenant.nama_cafe} berhasil diubah menjadi: {status_akses}'})


class MenuViewSet(viewsets.ModelViewSet):
    queryset = Menu.objects.all()
    serializer_class = MenuSerializer
    permission_classes = [MenuPermission]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        return filter_by_tenant(self.request, Menu.objects.all())

    def perform_create(self, serializer):
        profile = get_profile(self.request.user)
        if profile:
            serializer.save(tenant=profile.tenant)
            return
        tenant_id = self.request.data.get('tenant')
        if not (self.request.user.is_superuser and tenant_id):
            raise PermissionDenied('Tenant tidak ditemukan.')
        serializer.save(tenant=get_object_or_404(Tenant, pk=tenant_id))

    def perform_update(self, serializer):
        old_foto = serializer.instance.foto
        new_foto = serializer.validated_data.get('foto')
        instance = serializer.save()
        if new_foto and old_foto and old_foto.name != instance.foto.name:
            old_foto.delete(save=False)

    @action(detail=True, methods=['post'])
    def toggle_tersedia(self, request, pk=None):
        menu = self.get_object()
        value = request.data.get('tersedia', None)
        if value is None:
            menu.tersedia = not menu.tersedia
        else:
            menu.tersedia = str(value).lower() in ('1', 'true', 'yes', 'ya')
        menu.save(update_fields=['tersedia'])
        label = 'tersedia' if menu.tersedia else 'habis'
        return Response({
            'message': f'Menu "{menu.nama_menu}" sekarang {label}.',
            'data': MenuSerializer(menu, context={'request': request}).data,
        })


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by('-created_at')
    serializer_class = OrderSerializer
    permission_classes = [OrderPermission]

    def get_queryset(self):
        return filter_by_tenant(self.request, Order.objects.all().order_by('-created_at'))

    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_bukti(self, request, pk=None):
        order = self.get_object()

        if order.metode_pembayaran != 'QRIS':
            return Response({'error': 'Metode pembayaran pesanan ini adalah Tunai.'}, status=status.HTTP_400_BAD_REQUEST)
        if order.status_pesanan != 'Pending':
            return Response({'error': 'Pesanan sudah dikonfirmasi kasir.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = UploadBuktiSerializer(order, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            order.status_pesanan = 'Pending'
            order.save()

            return Response({
                'message': 'Bukti transfer berhasil diunggah. Menunggu konfirmasi kasir.',
                'data': OrderSerializer(order, context={'request': request}).data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def konfirmasi_kasir(self, request, pk=None):
        order = self.get_object()
        order.status_pesanan = 'Diproses'
        order.save()
        return Response({
            'message': 'Pesanan berhasil dikonfirmasi dan dikirim ke dapur.',
            'data': OrderSerializer(order, context={'request': request}).data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def selesaikan_pesanan(self, request, pk=None):
        order = self.get_object()
        order.status_pesanan = 'Selesai'
        order.save()
        return Response({
            'message': 'Pesanan selesai disajikan.',
            'data': OrderSerializer(order, context={'request': request}).data
        }, status=status.HTTP_200_OK)


class MejaViewSet(viewsets.ModelViewSet):
    queryset = Meja.objects.all()
    serializer_class = MejaSerializer
    permission_classes = [TenantUserWritePermission]

    def get_queryset(self):
        return filter_by_tenant(self.request, Meja.objects.all().order_by('nomor_meja'))

    def perform_create(self, serializer):
        profile = get_profile(self.request.user)
        if profile:
            if profile.role != 'owner':
                raise PermissionDenied('Hanya owner yang dapat menambah meja.')
            tenant = profile.tenant
        else:
            tenant_id = self.request.data.get('tenant')
            if not (self.request.user.is_superuser and tenant_id):
                raise PermissionDenied('Tenant tidak ditemukan.')
            tenant = get_object_or_404(Tenant, pk=tenant_id)
        nomor = serializer.validated_data['nomor_meja']
        if Meja.objects.filter(tenant=tenant, nomor_meja__iexact=nomor).exists():
            raise DRFValidationError({'nomor_meja': f'Meja {nomor} sudah ada.'})
        serializer.save(tenant=tenant)

    def perform_destroy(self, instance):
        profile = get_profile(self.request.user)
        if profile and profile.role != 'owner':
            raise PermissionDenied('Hanya owner yang dapat menghapus meja.')
        instance.delete()


def _cafe_choices():
    return Tenant.objects.filter(status='active').order_by('nama_cafe').values('nama_cafe', 'slug')


WA_RE = re.compile(r'\+?\d{10,15}')
REGISTER_FIELDS = ('nama_cafe', 'nama_owner', 'email_owner', 'whatsapp', 'alamat', 'owner_username', 'kasir_username')


def register_view(request):
    if request.method != 'POST':
        if get_profile(request.user):
            logout(request)
        return render(request, 'register.html', {'form': request.session.pop('register_form', {})})

    if request.POST.get('website'):
        messages.error(request, 'Pendaftaran tidak dapat diproses. Silakan coba lagi.')
        return redirect('register')
    if not batas_permintaan(request, 'daftar', maks=settings.DINEZY_DAFTAR_MAKS_PER_JAM, detik=3600):
        messages.error(request, 'Terlalu banyak percobaan pendaftaran dari jaringan ini. Coba lagi dalam satu jam.')
        return redirect('register')

    data = {k: ' '.join((request.POST.get(k) or '').split())[:200] for k in REGISTER_FIELDS}
    data['whatsapp'] = re.sub(r'[\s.\-()]', '', data['whatsapp'])
    errors = []
    if not all(data[k] for k in ('nama_cafe', 'nama_owner', 'email_owner', 'whatsapp', 'alamat')):
        errors.append('Semua data cafe wajib diisi.')
    try:
        validate_email(data['email_owner'])
    except ValidationError:
        errors.append('Format email tidak valid.')
    if data['whatsapp'] and not WA_RE.fullmatch(data['whatsapp']):
        errors.append('Nomor WhatsApp hanya boleh berisi angka (10–15 digit).')
    logo, err_logo = cek_gambar(request.FILES.get('logo'), 'Logo cafe', maks_mb=2, maks_sisi=800)
    qris, err_qris = cek_gambar(request.FILES.get('qris'), 'Gambar QRIS', wajib=False, maks_mb=3, maks_sisi=1600)
    errors += err_logo + err_qris
    errors += validate_new_account(data['owner_username'], request.POST.get('owner_password', ''),
                                   request.POST.get('owner_password2', ''), 'Owner', data['nama_owner'])
    errors += validate_new_account(data['kasir_username'], request.POST.get('kasir_password', ''),
                                   request.POST.get('kasir_password2', ''), 'Kasir')
    if data['owner_username'] and data['owner_username'].lower() == data['kasir_username'].lower():
        errors.append('Username Owner dan Kasir harus berbeda.')
    if request.POST.get('setuju') != 'on':
        errors.append('Anda perlu menyetujui syarat & ketentuan.')
    if data['nama_cafe'] and Tenant.objects.filter(nama_cafe__iexact=data['nama_cafe'],
                                                   email_owner__iexact=data['email_owner']).exists():
        errors.append('Cafe dengan nama dan email ini sudah terdaftar. Silakan login.')

    if errors:
        for e in errors:
            messages.error(request, e)
        request.session['register_form'] = data
        return redirect('register')

    with transaction.atomic():
        tenant = Tenant(
            nama_cafe=data['nama_cafe'], slug=unique_slug(data['nama_cafe']),
            nama_owner=data['nama_owner'], email_owner=data['email_owner'],
            whatsapp=data['whatsapp'], alamat=data['alamat'], status='active',
        )
        tenant.logo.save(logo.name, logo, save=False)
        if qris:
            tenant.qris_image.save(qris.name, qris, save=False)
        tenant.save()
        accounts = create_custom_accounts(tenant, data['owner_username'], request.POST['owner_password'],
                                          data['kasir_username'], request.POST['kasir_password'])
        catat_persetujuan_sk(tenant, client_ip(request))

    email_sent = send_credentials_email(tenant, accounts, request.build_absolute_uri('/'))
    owner = User.objects.get(username=data['owner_username'])
    login(request, owner, backend='django.contrib.auth.backends.ModelBackend')
    request.session.pop('register_form', None)
    request.session['register_result'] = {
        'nama_cafe': tenant.nama_cafe, 'email': tenant.email_owner, 'email_sent': email_sent,
        'accounts': [{'role': a['role'], 'username': a['username']} for a in accounts],
    }
    return redirect('owner_perjanjian', tenant_slug=tenant.slug)


def landing_view(request):
    dashboard_url = ''
    profile = get_profile(request.user)
    if profile and not request.user.is_superuser:
        target = 'owner_dashboard' if profile.role == 'owner' else 'kasir_dashboard'
        dashboard_url = redirect(target, tenant_slug=profile.tenant.slug).url
    return render(request, 'landing.html', {'dashboard_url': dashboard_url, 'hero': _hero_images()})


MASKOT_NAMES = ('MASKOT.png', 'maskot.png', 'Maskot.png', 'MASKOT.jpg', 'maskot.jpg', 'MASKOT.jpeg',
                'maskot.jpeg', 'MASKOT.webp', 'maskot.webp')


def _hero_images():
    from django.contrib.staticfiles import finders
    from django.templatetags.static import static

    for nama in MASKOT_NAMES:
        path = finders.find(f'core/img/{nama}')
        if path:
            mode = 'photo'
            try:
                from PIL import Image
                with Image.open(path) as im:
                    if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
                        alpha = im.convert('RGBA').getchannel('A')
                        if alpha.getextrema()[0] < 250:
                            mode = 'cutout'
            except Exception:
                pass
            return {'ada': True, 'src': static(f'core/img/{nama}'), 'mode': mode}
    return {'ada': False, 'src': static('core/img/hero-person.svg'), 'mode': 'cutout'}


def _find_tenant(value):
    value = (value or '').strip()
    if not value:
        return None
    return Tenant.objects.filter(Q(slug__iexact=value) | Q(nama_cafe__iexact=value)).first()


def _authenticate_flexible(request, username, password):
    kandidat = sorted(User.objects.filter(username__iexact=username), key=lambda u: u.username != username)
    if not kandidat:
        make_password(password)
    for obj in kandidat:
        for pw in dict.fromkeys([password, password.strip()]):
            if not pw:
                continue
            user = authenticate(request, username=obj.username, password=pw)
            if user is not None:
                return user, obj
    return None, (kandidat[0] if kandidat else None)


def _blocked_info(tenant):
    info = sync_tenant(tenant)
    return {
        'cafe': tenant.nama_cafe,
        'reason': tenant.lock_reason or 'manual',
        'total': info['total_overdue'] or info['total_unpaid'],
        'invoices': [{'nomor': i.nomor, 'periode': i.periode, 'total': i.total_bayar, 'denda': i.denda_berjalan,
                      'jatuh_tempo': i.jatuh_tempo.strftime('%d/%m/%Y')} for i in (info['overdue'] or info['unpaid'])],
        'wa': settings.DINEZY_ADMIN_WA,
    }


def _splash(request, user, tenant=None):
    request.session['dz_splash'] = {
        'nama': (user.get_full_name() or user.username)[:40],
        'cafe': tenant.nama_cafe if tenant else 'Panel Admin',
    }


def login_view(request):
    if request.method == 'POST':
        mode = request.POST.get('mode', 'cafe')
        cafe_input = (request.POST.get('cafe') or '').strip()
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''

        def fail(msg, blocked=None):
            messages.error(request, msg)
            request.session['login_cafe'] = cafe_input
            request.session['login_username'] = username
            request.session['login_mode'] = mode
            if blocked:
                request.session['login_blocked'] = blocked
            return redirect('login')

        if not username or not password:
            return fail('Username dan password wajib diisi.')
        if len(username) > 150 or len(password) > 128:
            return fail('Username atau password salah.')

        guard = LoginGuard(request, username)
        if guard.terkunci():
            return fail(f'Terlalu banyak percobaan masuk. Coba lagi dalam {guard.menit} menit.')
        user, user_obj = _authenticate_flexible(request, username, password)
        if user is None:
            guard.gagal(username)
            if user_obj is not None and not user_obj.is_active:
                return fail('Akun ini sedang dinonaktifkan. Hubungi admin.')
            return fail('Username atau password salah.')
        guard.berhasil()

        nxt = request.POST.get('next') or ''
        safe_next = nxt if nxt.startswith('/') and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}) else ''

        if mode == 'admin':
            if not user.is_staff:
                return fail('Akun ini bukan akun admin. Pilih "Owner / Kasir" untuk masuk ke dashboard cafe.')
            login(request, user)
            _splash(request, user)
            return redirect(safe_next or 'panel_dashboard')

        profile = get_profile(user)
        if not profile:
            if user.is_staff:
                login(request, user)
                _splash(request, user)
                return redirect('panel_dashboard')
            return fail('Akun ini belum terhubung ke cafe mana pun. Minta admin menghubungkan akun '
                        '(Panel Admin > Cafe) atau jalankan "python manage.py buat_akun_cafe".')

        tenant = profile.tenant
        if cafe_input:
            dipilih = _find_tenant(cafe_input)
            if dipilih is None:
                return fail('Cafe tidak ditemukan. Pilih cafe dari daftar.')
            if dipilih.id != tenant.id:
                return fail(f'Akun ini tidak terdaftar di cafe "{dipilih.nama_cafe}".')

        if tenant.status != 'active':
            return fail('Cafe ini berstatus nonaktif. Silakan hubungi admin Dinezy.')

        sync_tenant(tenant)
        if tenant.is_locked:
            info = _blocked_info(tenant)
            if info['reason'] == 'tagihan':
                return fail('Anda belum membayar tagihan layanan Dinezy. Akun cafe diblokir sementara.', info)
            return fail('Akses cafe ini sedang dikunci oleh admin. Silakan hubungi admin Dinezy.', info)

        login(request, user)
        _splash(request, user, tenant)
        if decrypt(profile.pw_enc) != password:
            simpan_password(user, password)
        if safe_next.startswith('/invoice/') and profile.role == 'owner':
            return redirect(safe_next)
        if profile.role == 'owner':
            return redirect('owner_dashboard', tenant_slug=tenant.slug)
        return redirect('kasir_dashboard', tenant_slug=tenant.slug)

    if request.user.is_authenticated:
        logout(request)

    cafe = request.session.pop('login_cafe', '') or request.GET.get('cafe', '')
    tenant = _find_tenant(cafe)
    context = {
        'cafe': tenant.slug if tenant else cafe,
        'username': request.session.pop('login_username', ''),
        'mode': request.session.pop('login_mode', '') or request.GET.get('mode', 'cafe'),
        'blocked': request.session.pop('login_blocked', None),
        'next': request.GET.get('next', ''),
        'cafes': _cafe_choices(),
    }
    return render(request, 'login.html', context)


def _check_role(request, tenant_slug, role):
    tenant = get_object_or_404(Tenant, slug=tenant_slug)
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.tenant_id != tenant.id or profile.role != role:
        return tenant, False
    return tenant, True


def _blocked_redirect(request, tenant):
    sync_tenant(tenant)
    if not tenant.is_locked:
        return None
    info = _blocked_info(tenant)
    logout(request)
    messages.error(request, 'Anda belum membayar tagihan layanan Dinezy. Akun cafe diblokir sementara.'
                   if info['reason'] == 'tagihan' else 'Akses cafe ini sedang dikunci oleh admin.')
    request.session['login_blocked'] = info
    request.session['login_cafe'] = tenant.slug
    return redirect('login')


@login_required(login_url='/login/')
@ensure_csrf_cookie
def kasir_page(request, tenant_slug):
    tenant, ok = _check_role(request, tenant_slug, 'kasir')
    if not ok:
        return render(request, 'forbidden.html',
                      {'pesan': 'Anda tidak memiliki izin untuk halaman kasir cafe ini.'}, status=403)
    blocked = _blocked_redirect(request, tenant)
    if blocked:
        return blocked
    return render(request, 'kasir.html', {'tenant': tenant, 'banner': banner_aktif(tenant)})


@ensure_csrf_cookie
def menu_page(request, slug):
    tenant = get_object_or_404(Tenant, slug=slug)
    from .billing import tarif
    return render(request, 'menu.html', {'tenant_slug': slug, 'tenant': tenant, 'biaya_layanan': tarif(tenant)})


@login_required(login_url='/login/')
@ensure_csrf_cookie
def owner_dashboard(request, tenant_slug):
    tenant, ok = _check_role(request, tenant_slug, 'owner')
    if not ok:
        return render(request, 'forbidden.html',
                      {'pesan': 'Anda bukan owner dari cafe ini.'}, status=403)
    blocked = _blocked_redirect(request, tenant)
    if blocked:
        return blocked
    kasir_accounts = User.objects.filter(profile__tenant=tenant, profile__role='kasir')
    from .perjanjian import batas_ttd, get_pks
    pks = get_pks(tenant)
    pesan = list(untuk_cafe(tenant)[:60])
    return render(request, 'owner.html', {
        'pks': pks, 'pks_batas': batas_ttd(pks),
        'pesan': pesan, 'pesan_baru': sum(1 for m in pesan if not m.sudah_dibaca), 'banner': banner_aktif(tenant),
        'ikon_pesan': IKON,
        'tenant': tenant, 'kasir_accounts': kasir_accounts, 'kategori_choices': Menu.KATEGORI_CHOICES,
        'tagihan': status_tagihan(tenant), 'invoices': tenant.invoices.all()[:24],
        'bulan_ini': running_month(tenant), 'tarif': tarif(tenant),
        'print_types': Tenant.PRINT_TYPES, 'kitchen_choices': Tenant.KITCHEN_PRINT,
    })


@login_required(login_url='/login/')
def owner_laporan(request, tenant_slug):
    from datetime import date, datetime, time, timedelta
    from django.utils import timezone as tz
    from .models import BULAN_ID

    tenant, ok = _check_role(request, tenant_slug, 'owner')
    if not ok:
        return render(request, 'forbidden.html', {'pesan': 'Anda bukan owner dari cafe ini.'}, status=403)
    blocked = _blocked_redirect(request, tenant)
    if blocked:
        return blocked

    today = tz.localdate()

    def parse(v, default):
        try:
            return date.fromisoformat(v)
        except (TypeError, ValueError):
            return default
    mulai = parse(request.GET.get('mulai'), today.replace(day=1))
    sampai = parse(request.GET.get('sampai'), today)
    if sampai < mulai:
        mulai, sampai = sampai, mulai
    zona = tz.get_current_timezone()
    start = tz.make_aware(datetime.combine(mulai, time.min), zona)
    end = tz.make_aware(datetime.combine(sampai + timedelta(days=1), time.min), zona)

    semua = Order.objects.filter(tenant=tenant, created_at__gte=start, created_at__lt=end)
    orders = list(semua.filter(status_pesanan__in=('Diproses', 'Selesai')).prefetch_related('items__menu'))
    pending = semua.filter(status_pesanan='Pending').count()

    pendapatan = sum(o.total_harga for o in orders)
    layanan = sum(o.biaya_layanan or 0 for o in orders)
    nota = len(orders)
    item = 0
    harian, bayar, menu_map = {}, {}, {}
    for o in orders:
        tgl_lokal = tz.localtime(o.created_at).date()
        metode = 'QRIS' if (o.metode_pembayaran or '').upper() == 'QRIS' else 'TUNAI'
        d = harian.setdefault(tgl_lokal, {'nota': 0, 'TUNAI': 0, 'QRIS': 0, 'total': 0})
        d['nota'] += 1
        d[metode] += o.total_harga
        d['total'] += o.total_harga
        b = bayar.setdefault(metode, {'nota': 0, 'total': 0})
        b['nota'] += 1
        b['total'] += o.total_harga
        for it in o.items.all():
            item += it.jumlah
            nama = it.menu.nama_menu if it.menu_id else 'Menu dihapus'
            kat = (getattr(it.menu, 'kategori', '') or 'Lainnya')
            mm = menu_map.setdefault((kat, nama), {'nama': nama, 'qty': 0, 'total': 0, 'harga': it.harga_satuan})
            mm['qty'] += it.jumlah
            mm['total'] += it.jumlah * it.harga_satuan

    hari = [{'tgl': k, **v} for k, v in sorted(harian.items())]
    total_tunai = sum(h['TUNAI'] for h in hari)
    total_qris = sum(h['QRIS'] for h in hari)
    bayar_list = [{'metode': 'Tunai', **bayar.get('TUNAI', {'nota': 0, 'total': 0})},
                  {'metode': 'QRIS', **bayar.get('QRIS', {'nota': 0, 'total': 0})}]

    kelompok = {}
    for (kat, _), mm in sorted(menu_map.items(), key=lambda x: (x[0][0], -x[1]['total'])):
        g = kelompok.setdefault(kat, {'kategori': kat, 'menu': [], 'qty': 0, 'total': 0})
        g['menu'].append(mm)
        g['qty'] += mm['qty']
        g['total'] += mm['total']
    kategori_list = sorted(kelompok.values(), key=lambda g: -g['total'])

    if mulai.day == 1 and (sampai + timedelta(days=1)).day == 1 and mulai.month == sampai.month:
        label = f"{BULAN_ID[mulai.month]} {mulai.year}"
    else:
        label = f"{mulai.day} {BULAN_ID[mulai.month]} {mulai.year} – {sampai.day} {BULAN_ID[sampai.month]} {sampai.year}"
    nomor = f"LAP/{tenant.slug.upper()}/{mulai.strftime('%Y%m%d')}-{sampai.strftime('%Y%m%d')}"

    return render(request, 'laporan.html', {
        'tenant': tenant, 'mulai': mulai, 'sampai': sampai, 'label': label, 'today': today, 'nomor': nomor,
        'kpi': {'pendapatan': pendapatan, 'nota': nota, 'item': item, 'pending': pending,
                'tunai': total_tunai, 'qris': total_qris, 'hari_aktif': len(hari),
                'layanan': layanan, 'penjualan': pendapatan - layanan},
        'hari': hari, 'bayar_list': bayar_list, 'kategori_list': kategori_list,
        'dicetak': tz.localtime(), 'oleh': request.user.get_full_name() or request.user.username,
    })


@login_required(login_url='/login/')
@require_POST
def owner_setelan(request, tenant_slug):
    tenant, ok = _check_role(request, tenant_slug, 'owner')
    if not ok:
        return render(request, 'forbidden.html', {'pesan': 'Anda bukan owner dari cafe ini.'}, status=403)
    logo, errors = cek_gambar(request.FILES.get('logo'), 'Logo cafe', wajib=False, maks_mb=2, maks_sisi=800)
    qris, err_qris = cek_gambar(request.FILES.get('qris'), 'Gambar QRIS', wajib=False, maks_mb=3, maks_sisi=1600)
    errors += err_qris
    pt = request.POST.get('print_type')
    kp = request.POST.get('kitchen_print')
    if pt not in dict(Tenant.PRINT_TYPES):
        errors.append('Jenis printer tidak valid.')
    if kp not in dict(Tenant.KITCHEN_PRINT):
        errors.append('Pilihan cetak dapur tidak valid.')
    if errors:
        for e in errors:
            messages.error(request, e, extra_tags='setelan')
    else:
        tenant.print_type, tenant.kitchen_print = pt, kp
        tenant.nota_footer = (request.POST.get('nota_footer') or '').strip()[:120]
        tenant.nota_show_qr = request.POST.get('nota_show_qr') == 'on'
        if logo:
            ganti_file(tenant.logo, logo)
        if qris:
            ganti_file(tenant.qris_image, qris)
        elif request.POST.get('hapus_qris') == '1' and tenant.qris_image:
            tenant.qris_image.delete(save=False)
        tenant.save()
        messages.success(request, 'Setelan berhasil disimpan.', extra_tags='setelan')
    return redirect(f"{reverse('owner_dashboard', args=[tenant.slug])}#setelan")


def custom_logout(request):
    logout(request)
    return redirect('/login/')


def csrf_failure(request, reason=''):
    return render(request, 'forbidden.html', {
        'pesan': 'Sesi formulir sudah kedaluwarsa atau tidak valid. Muat ulang halaman lalu coba lagi.',
    }, status=403)
