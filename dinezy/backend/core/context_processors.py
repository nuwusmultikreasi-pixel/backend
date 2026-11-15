from django.conf import settings
from django.db.models import Count, Sum

from .billing import aturan_denda


def _rupiah(n):
    return f"Rp {n:,.0f}".replace(',', '.')


def _angka(x):
    return f"{x:g}".replace('.', ',')


def brand(request):
    return {
        'brand': {
            'nama': settings.DINEZY_NAMA,
            'tagline': settings.DINEZY_TAGLINE,
            'deskripsi': settings.DINEZY_DESKRIPSI,
            'perusahaan': settings.DINEZY_PERUSAHAAN_NAMA,
        }
    }


def admin_stats(request):
    if not request.path.startswith('/' + settings.DINEZY_ADMIN_PATH):
        return {}
    from .models import Order, Tenant

    tarif = int(getattr(settings, 'DINEZY_TARIF_PER_NOTA', 1500))
    tenants = Tenant.objects.annotate(n=Count('orders'), omset=Sum('orders__total_harga')).order_by('-id')
    tenant_list = [{
        'id': t.id, 'nama_cafe': t.nama_cafe, 'slug': t.slug, 'status': t.status,
        'total_orders': t.n, 'omset': t.omset or 0, 'omset_formatted': _rupiah(t.omset or 0),
        'tagihan_app': t.n * tarif, 'tagihan_app_formatted': _rupiah(t.n * tarif)[3:],
    } for t in tenants]
    total_omset = Order.objects.aggregate(s=Sum('total_harga'))['s'] or 0
    return {
        'total_tenants': len(tenant_list),
        'total_orders': Order.objects.count(),
        'total_omset': total_omset,
        'total_omset_formatted': _rupiah(total_omset),
        'tenant_list': tenant_list,
    }


def ketentuan_denda(request):
    a = aturan_denda()
    return {'denda': {**a, 'permil_teks': _angka(a['permil']), 'maks_teks': _angka(a['maks'])}}
