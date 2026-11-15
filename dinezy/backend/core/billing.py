import calendar
from datetime import date, datetime, time

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from .models import BULAN_ID, Invoice, Order, Tenant

NOTA_STATUSES = ('Diproses', 'Selesai')


def tarif_standar():
    return int(getattr(settings, 'DINEZY_TARIF_PER_NOTA', 1500))


def tarif(tenant=None):
    if tenant is not None and getattr(tenant, 'tarif_layanan', None) is not None:
        return int(tenant.tarif_layanan)
    return tarif_standar()


def aturan_denda():
    g = lambda k, d: getattr(settings, k, d)
    return {
        'tenggang': int(g('DINEZY_DENDA_TENGGANG_HARI', 3)),
        'permil': float(g('DINEZY_DENDA_PERMIL_HARI', 1)),
        'maks': float(g('DINEZY_DENDA_MAKS_PERSEN', 10)),
    }


def hari_denda(invoice, today=None):
    if invoice.status == 'paid':
        akhir = timezone.localtime(invoice.dibayar_pada).date() if invoice.dibayar_pada else invoice.jatuh_tempo
    else:
        akhir = today or timezone.localdate()
    return max(0, (akhir - invoice.jatuh_tempo).days - aturan_denda()['tenggang'])


def hitung_denda(invoice, today=None):
    if invoice.status == 'paid':
        return invoice.denda or 0
    hari = hari_denda(invoice, today)
    if hari <= 0 or not invoice.total:
        return 0
    a = aturan_denda()
    nilai = round(invoice.total * a['permil'] / 1000 * hari)
    return int(min(nilai, round(invoice.total * a['maks'] / 100)))


def _month_add(y, m, n):
    m0 = (y * 12 + (m - 1)) + n
    return m0 // 12, m0 % 12 + 1


def _month_range(y, m):
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(date(y, m, 1), time.min), tz)
    ny, nm = _month_add(y, m, 1)
    end = timezone.make_aware(datetime.combine(date(ny, nm, 1), time.min), tz)
    return start, end


def _nota_qs(tenant, y, m):
    start, end = _month_range(y, m)
    return Order.objects.filter(tenant=tenant, status_pesanan__in=NOTA_STATUSES,
                                created_at__gte=start, created_at__lt=end)


def count_nota(tenant, y, m):
    return _nota_qs(tenant, y, m).count()


def hitung_bulan(tenant, y, m, tarif_cadangan=None):
    agg = _nota_qs(tenant, y, m).aggregate(n=Count('id'), fee=Sum('biaya_layanan'),
                                           nol=Count('id', filter=Q(biaya_layanan=0)))
    cadangan = tarif(tenant) if tarif_cadangan is None else tarif_cadangan
    return agg['n'], (agg['fee'] or 0) + agg['nol'] * cadangan


def penjualan_bulan(tenant, y, m):
    agg = _nota_qs(tenant, y, m).aggregate(n=Count('id'), total=Sum('total_harga'), fee=Sum('biaya_layanan'))
    n, jual = agg['n'], (agg['total'] or 0) - (agg['fee'] or 0)
    return {'nota': n, 'penjualan': jual, 'rata': round(jual / n) if n else 0}


def billing_start():
    raw = getattr(settings, 'DINEZY_BILLING_START', '') or '2026-11'
    y, m = raw.split('-')[:2]
    return int(y), int(m)


def due_dates(y, m):
    ty, tm = _month_add(y, m, 1)
    terbit = date(ty, tm, 1)
    jatuh_tempo = date(ty, tm, calendar.monthrange(ty, tm)[1])
    return terbit, jatuh_tempo


@transaction.atomic
def sync_tenant(tenant, today=None):
    today = today or timezone.localdate()
    by, bm = billing_start()
    created = timezone.localtime(tenant.created_at).date() if tenant.created_at else today
    y, m = max((by, bm), (created.year, created.month))
    last_y, last_m = _month_add(today.year, today.month, -1)

    while (y, m) <= (last_y, last_m):
        inv = Invoice.objects.filter(tenant=tenant, tahun=y, bulan=m).first()
        jumlah, total = hitung_bulan(tenant, y, m, inv.tarif if inv else None)
        if inv is None and jumlah > 0:
            terbit, tempo = due_dates(y, m)
            Invoice.objects.create(tenant=tenant, tahun=y, bulan=m, jumlah_nota=jumlah, tarif=tarif(tenant),
                                   total=total, tanggal_terbit=terbit, jatuh_tempo=tempo)
        elif inv is not None and inv.status == 'unpaid' and (inv.jumlah_nota, inv.total) != (jumlah, total):
            inv.jumlah_nota, inv.total = jumlah, total
            inv.save(update_fields=['jumlah_nota', 'total'])
        y, m = _month_add(y, m, 1)

    unpaid = tenant.invoices.filter(status='unpaid')
    overdue = unpaid.filter(jatuh_tempo__lt=today)
    total_unpaid = sum(i.total + hitung_denda(i, today) for i in unpaid)

    fields = []
    if tenant.unpaid_bill != total_unpaid:
        tenant.unpaid_bill = total_unpaid
        fields.append('unpaid_bill')
    if overdue.exists() and not tenant.is_locked:
        tenant.is_locked, tenant.lock_reason = True, 'tagihan'
        fields += ['is_locked', 'lock_reason']
    elif not overdue.exists() and tenant.is_locked and tenant.lock_reason == 'tagihan':
        tenant.is_locked, tenant.lock_reason = False, ''
        fields += ['is_locked', 'lock_reason']
    if fields:
        tenant.save(update_fields=fields)

    return status_tagihan(tenant, today)


def running_month(tenant, today=None):
    today = today or timezone.localdate()
    jumlah, total = hitung_bulan(tenant, today.year, today.month)
    terbit, tempo = due_dates(today.year, today.month)
    return {'jumlah_nota': jumlah, 'total': total, 'tarif': tarif(tenant), 'terbit': terbit, 'jatuh_tempo': tempo,
            'periode': f"{BULAN_ID[today.month]} {today.year}"}


def status_tagihan(tenant, today=None):
    today = today or timezone.localdate()
    unpaid = list(tenant.invoices.filter(status='unpaid').order_by('tahun', 'bulan'))
    overdue = [i for i in unpaid if i.jatuh_tempo < today]
    return {
        'unpaid': unpaid,
        'overdue': overdue,
        'total_unpaid': sum(i.total + hitung_denda(i, today) for i in unpaid),
        'total_overdue': sum(i.total + hitung_denda(i, today) for i in overdue),
        'total_denda': sum(hitung_denda(i, today) for i in unpaid),
        'next_due': min((i.jatuh_tempo for i in unpaid), default=None),
        'blocked': tenant.is_locked,
        'lock_reason': tenant.lock_reason,
    }


def sync_all(today=None):
    for t in Tenant.objects.all():
        sync_tenant(t, today)


@transaction.atomic
def mark_paid(invoice, catatan=''):
    invoice.denda = hitung_denda(invoice)
    invoice.status = 'paid'
    invoice.dibayar_pada = timezone.now()
    if catatan:
        invoice.catatan = catatan[:255]
    invoice.save(update_fields=['status', 'dibayar_pada', 'catatan', 'denda'])
    return sync_tenant(invoice.tenant)


@transaction.atomic
def mark_unpaid(invoice):
    invoice.status, invoice.dibayar_pada, invoice.denda = 'unpaid', None, 0
    invoice.save(update_fields=['status', 'dibayar_pada', 'denda'])
    return sync_tenant(invoice.tenant)
