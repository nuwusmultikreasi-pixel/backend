from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.db.models import Sum
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .accounts import ensure_cafe_accounts, send_credentials_email
from .billing import (NOTA_STATUSES, _month_add, _month_range, hitung_bulan, mark_paid, mark_unpaid,
                      penjualan_bulan, running_month, status_tagihan, sync_all, sync_tenant, tarif, tarif_standar)
from .models import BULAN_ID, Invoice, Order, Tenant, UserProfile
from .secretbox import decrypt, simpan_password

panel_required = staff_member_required(login_url='/login/?mode=admin')


def _cafe_rows(today):
    rows = []
    for t in Tenant.objects.all().order_by('nama_cafe'):
        st = status_tagihan(t, today)
        run = running_month(t, today)
        if t.is_locked:
            badge = ('red', 'Diblokir · tagihan') if t.lock_reason == 'tagihan' else ('amber', 'Dikunci manual')
        elif t.status != 'active':
            badge = ('gray', 'Nonaktif')
        elif st['unpaid']:
            badge = ('amber', 'Ada tagihan')
        else:
            badge = ('green', 'Aktif')
        ly, lm = _month_add(today.year, today.month, -1)
        jual, jual_lalu = penjualan_bulan(t, today.year, today.month), penjualan_bulan(t, ly, lm)
        tf = tarif(t)
        ref = jual['rata'] or jual_lalu['rata']
        rows.append({'t': t, 'st': st, 'run': run, 'badge': badge, 'jual': jual, 'jual_lalu': jual_lalu,
                     'tarif': tf, 'khusus': t.tarif_layanan is not None,
                     'porsi': round(tf / ref * 100, 1) if ref else None,
                     'akun': list(t.users.values_list('user__username', 'role'))})
    return rows


@panel_required
def dashboard(request):
    today = timezone.localdate()
    sync_all(today)
    rows = _cafe_rows(today)
    start, end = _month_range(today.year, today.month)
    nota_bulan_ini = Order.objects.filter(status_pesanan__in=NOTA_STATUSES, created_at__gte=start, created_at__lt=end).count()

    chart = []
    for i in range(5, -1, -1):
        y, m = _month_add(today.year, today.month, -i)
        s, e = _month_range(y, m)
        n = tot = 0
        for t in Tenant.objects.all():
            a, b = hitung_bulan(t, y, m)
            n, tot = n + a, tot + b
        chart.append({'label': f"{BULAN_ID[m][:3]} {str(y)[2:]}", 'nota': n, 'total': tot})
    peak = max((c['total'] for c in chart), default=0) or 1
    for c in chart:
        c['pct'] = round(c['total'] / peak * 100)

    inv = Invoice.objects.all()
    ctx = {
        'active': 'dashboard', 'rows': rows, 'chart': chart,
        'kpi': {
            'cafe': len(rows),
            'diblokir': sum(1 for r in rows if r['t'].is_locked),
            'nota_bulan_ini': nota_bulan_ini,
            'estimasi_bulan_ini': sum(r['run']['total'] for r in rows),
            'belum_dibayar': inv.filter(status='unpaid').aggregate(s=Sum('total'))['s'] or 0,
            'jatuh_tempo': inv.filter(status='unpaid', jatuh_tempo__lt=today).aggregate(s=Sum('total'))['s'] or 0,
            'lunas_total': inv.filter(status='paid').aggregate(s=Sum('total'))['s'] or 0,
        },
        'recent': inv.select_related('tenant')[:6],
        'tarif': tarif_standar(), 'today': today,
    }
    return render(request, 'panel/dashboard.html', ctx)


@panel_required
def cafe_list(request):
    today = timezone.localdate()
    sync_all(today)
    q = (request.GET.get('q') or '').strip().lower()
    rows = _cafe_rows(today)
    if q:
        rows = [r for r in rows if q in r['t'].nama_cafe.lower() or q in r['t'].slug.lower() or q in (r['t'].nama_owner or '').lower()]
    return render(request, 'panel/cafe.html', {'active': 'cafe', 'rows': rows, 'q': q, 'tarif': tarif_standar(),
                                               'bulan': BULAN_ID[today.month], 'bulan_lalu': BULAN_ID[_month_add(today.year, today.month, -1)[1]]})


@panel_required
@require_POST
def cafe_tarif(request, pk):
    t = get_object_or_404(Tenant, pk=pk)
    raw = (request.POST.get('tarif') or '').replace('.', '').replace(',', '').strip()
    if request.POST.get('standar') == '1' or raw == '':
        t.tarif_layanan = None
    else:
        if not raw.isdigit() or not (0 <= int(raw) <= 50000):
            messages.error(request, 'Tarif tidak valid. Isi angka rupiah antara 0 dan 50.000.')
            return redirect('panel_cafe')
        t.tarif_layanan = int(raw)
    t.tarif_diubah = timezone.now()
    t.save(update_fields=['tarif_layanan', 'tarif_diubah'])
    baru = f"Rp {tarif(t):,}".replace(',', '.')
    messages.success(request, f'Biaya layanan {t.nama_cafe} sekarang {baru} per nota'
                     + (' (tarif standar).' if t.tarif_layanan is None else '.') + ' Berlaku untuk pesanan berikutnya.')
    return redirect(request.POST.get('next') or 'panel_cafe')


@panel_required
@require_POST
def cafe_kunci(request, pk):
    t = get_object_or_404(Tenant, pk=pk)
    if t.is_locked:
        t.is_locked, t.lock_reason = False, ''
        t.save(update_fields=['is_locked', 'lock_reason'])
        info = sync_tenant(t)
        if t.is_locked:
            messages.warning(request, f'{t.nama_cafe} tetap diblokir karena masih ada tagihan lewat jatuh tempo '
                             f'(Rp {info["total_overdue"]:,}). Tandai tagihan lunas terlebih dahulu.'.replace(',', '.'))
        else:
            messages.success(request, f'Kunci {t.nama_cafe} dibuka. Owner & Kasir dapat login kembali.')
    else:
        t.is_locked, t.lock_reason = True, 'manual'
        t.save(update_fields=['is_locked', 'lock_reason'])
        messages.success(request, f'{t.nama_cafe} dikunci. Owner & Kasir tidak dapat login.')
    return redirect(request.POST.get('next') or 'panel_cafe')


@panel_required
@require_POST
def cafe_akun(request, pk):
    t = get_object_or_404(Tenant, pk=pk)
    reset = request.POST.get('reset') == '1'
    akun = ensure_cafe_accounts(t, reset_password=reset)
    if not akun:
        messages.info(request, f'{t.nama_cafe}: akun Owner & Kasir sudah lengkap.')
    else:
        terkirim = send_credentials_email(t, akun, request.build_absolute_uri('/'))
        messages.success(request, f"Password {t.nama_cafe} diperbarui — " +
                         (f"dikirim ke {t.email_owner}." if terkirim else "email gagal terkirim, lihat password di halaman ini."))
    return redirect(f"{reverse('panel_akun')}?sorot={t.pk}#cafe-{t.pk}")


@panel_required
def akun_list(request):
    q = (request.GET.get('q') or '').strip().lower()
    cafes = []
    for t in Tenant.objects.order_by('nama_cafe'):
        if q and q not in t.nama_cafe.lower() and q not in t.slug.lower():
            continue
        akun = []
        for p in UserProfile.objects.filter(tenant=t).select_related('user').order_by('-role'):
            akun.append({'p': p, 'u': p.user, 'pw': decrypt(p.pw_enc), 'diset': p.pw_set_at,
                         'login': p.user.last_login})
        cafes.append({'t': t, 'akun': akun})
    total = sum(len(c['akun']) for c in cafes)
    tersimpan = sum(1 for c in cafes for a in c['akun'] if a['pw'])
    return render(request, 'panel/akun.html', {'active': 'akun', 'cafes': cafes, 'q': q,
                                               'total': total, 'tersimpan': tersimpan,
                                               'sorot': request.GET.get('sorot', '')})


@panel_required
@require_POST
def akun_password(request, pk):
    p = get_object_or_404(UserProfile.objects.select_related('user', 'tenant'), pk=pk)
    pw = (request.POST.get('password') or '').strip()
    back = f"{reverse('panel_akun')}?sorot={p.tenant_id}#cafe-{p.tenant_id}"
    if len(pw) < 8 or ' ' in pw:
        messages.error(request, 'Password minimal 8 karakter dan tanpa spasi.')
        return redirect(back)
    p.user.set_password(pw)
    p.user.is_active = True
    p.user.save()
    simpan_password(p.user, pw)
    messages.success(request, f'Password {p.get_role_display()} "{p.user.username}" ({p.tenant.nama_cafe if p.tenant else "-"}) berhasil diubah.')
    return redirect(back)


@panel_required
def tagihan_list(request):
    today = timezone.localdate()
    sync_all(today)
    status = request.GET.get('status', '')
    cafe = request.GET.get('cafe', '')
    qs = Invoice.objects.select_related('tenant')
    if status == 'unpaid':
        qs = qs.filter(status='unpaid')
    elif status == 'overdue':
        qs = qs.filter(status='unpaid', jatuh_tempo__lt=today)
    elif status == 'paid':
        qs = qs.filter(status='paid')
    if cafe:
        qs = qs.filter(tenant__slug=cafe)
    totals = qs.aggregate(total=Sum('total'), nota=Sum('jumlah_nota'))
    running = [{'t': t, 'run': running_month(t, today)} for t in Tenant.objects.order_by('nama_cafe')]
    return render(request, 'panel/tagihan.html', {
        'active': 'tagihan', 'invoices': qs, 'status': status, 'cafe': cafe, 'totals': totals,
        'cafes': Tenant.objects.order_by('nama_cafe'), 'running': running, 'today': today, 'tarif': tarif(),
        'periode_berjalan': f"{BULAN_ID[today.month]} {today.year}",
    })


@panel_required
@require_POST
def tagihan_bayar(request, pk):
    inv = get_object_or_404(Invoice, pk=pk)
    if request.POST.get('batal') == '1':
        mark_unpaid(inv)
        messages.info(request, f'{inv.nomor} dikembalikan ke status Belum Dibayar.')
    else:
        info = mark_paid(inv, request.POST.get('catatan', '').strip())
        pesan = f'{inv.nomor} ({inv.tenant.nama_cafe}) ditandai LUNAS.'
        if not info['blocked']:
            pesan += ' Akun cafe aktif kembali.'
        messages.success(request, pesan)
    return redirect(request.POST.get('next') or 'panel_tagihan')


def invoice_view(request, pk):
    inv = get_object_or_404(Invoice.objects.select_related('tenant'), pk=pk)
    user = request.user
    if not user.is_authenticated:
        return redirect(f'/login/?next=/invoice/{pk}/')
    profile = getattr(user, 'profile', None)
    if not (user.is_staff or (profile and profile.tenant_id == inv.tenant_id and profile.role == 'owner')):
        return HttpResponseForbidden('Anda tidak berhak melihat invoice ini.')

    start, end = _month_range(inv.tahun, inv.bulan)
    harian = {}
    for dt, fee in Order.objects.filter(tenant=inv.tenant, status_pesanan__in=NOTA_STATUSES,
                                        created_at__gte=start, created_at__lt=end).values_list('created_at', 'biaya_layanan'):
        tgl = timezone.localtime(dt).date()
        n, s = harian.get(tgl, (0, 0))
        harian[tgl] = (n + 1, s + (fee or inv.tarif))
    rows = [{'tgl': d, 'n': n, 'subtotal': s} for d, (n, s) in sorted(harian.items())]
    return render(request, 'panel/invoice.html', {
        'inv': inv, 'rows': rows, 'is_admin': user.is_staff,
        'pay': {'bank': settings.DINEZY_PAYMENT_BANK, 'rek': settings.DINEZY_PAYMENT_ACCOUNT, 'nama': settings.DINEZY_PAYMENT_NAME,
                'wa': settings.DINEZY_ADMIN_WA, 'alamat': settings.DINEZY_COMPANY_ADDRESS},
    })
