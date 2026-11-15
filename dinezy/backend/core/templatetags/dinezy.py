from django import template

register = template.Library()


@register.filter
def rupiah(value):
    try:
        return 'Rp ' + f"{int(value or 0):,}".replace(',', '.')
    except (TypeError, ValueError):
        return 'Rp 0'


@register.filter
def angka(value):
    try:
        return f"{int(value or 0):,}".replace(',', '.')
    except (TypeError, ValueError):
        return '0'


BULAN = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
BULAN_PANJANG = ['', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus',
                 'September', 'Oktober', 'November', 'Desember']


@register.filter
def tgl(value, panjang=False):
    if not value:
        return '-'
    nama = BULAN_PANJANG if panjang else BULAN
    return f"{value.day} {nama[value.month]} {value.year}"


@register.simple_tag
def dz_messages_json(messages):
    import json
    from django.utils.safestring import mark_safe
    data = []
    for m in messages:
        tags = (m.tags or 'info').split()
        tipe = next((t for t in tags if t in ('success', 'warning', 'error', 'info')), 'info')
        data.append({'type': tipe, 'text': str(m), 'timeout': 7000 if tipe in ('warning', 'error') else 5200})
    if not data:
        return ''
    raw = json.dumps(data).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    return mark_safe(f'<script id="dz-messages" type="application/json">{raw}</script>')


@register.simple_tag(takes_context=True)
def dz_splash(context):
    request = context.get('request')
    if request is None or not hasattr(request, 'session'):
        return None
    return request.session.pop('dz_splash', None)


@register.simple_tag
def tarif_nota():
    from core.billing import tarif
    return rupiah(tarif())


@register.filter
def get_item(d, key):
    try:
        return d.get(key, '')
    except AttributeError:
        return ''
