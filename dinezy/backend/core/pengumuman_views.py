from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from .models import Pengumuman, Tenant
from .panel import panel_required
from .pengumuman import (IKON, ISIAN, KATEGORI_FORMAL, MAKS_ISI, TEMPLAT, WARNA, buat_nomor, isi_untuk,
                         tandai_dibaca, untuk_cafe)
from .perjanjian import perusahaan, tanggal_panjang

MAKS_LAMPIRAN = 5 * 1024 * 1024


def _konteks_surat(p, tenant, mode, kembali):
    return {
        'p': p, 't': tenant, 'p1': perusahaan(), 'isi': isi_untuk(p, tenant), 'mode': mode, 'kembali': kembali,
        'formal': p.kategori in KATEGORI_FORMAL, 'tanggal': tanggal_panjang(p.dibuat).split(', ', 1)[-1],
        'ikon': IKON.get(p.kategori, 'fa-circle-info'),
    }


def _penerima_teks(p, total_cafe):
    return f'Semua cafe ({total_cafe})' if p.penerima == 'semua' else f'{p.tenants.count()} cafe terpilih'


@panel_required
def panel_pengumuman(request):
    total_cafe = Tenant.objects.count()
    rows = []
    for p in Pengumuman.objects.annotate(n_baca=Count('dibaca', distinct=True)).prefetch_related('tenants'):
        target = total_cafe if p.penerima == 'semua' else p.tenants.count()
        rows.append({'p': p, 'target': target, 'penerima': _penerima_teks(p, total_cafe),
                     'warna': WARNA.get(p.kategori, 'gray'), 'ikon': IKON.get(p.kategori, 'fa-circle-info')})
    return render(request, 'panel/pengumuman.html', {'active': 'pengumuman', 'rows': rows, 'now_dt': timezone.now()})


def _simpan(request, p):
    data = request.POST
    err = []
    kategori = data.get('kategori', '')
    judul = ' '.join((data.get('judul') or '').split())[:150]
    isi = (data.get('isi') or '').replace('\r\n', '\n').strip()
    penerima = data.get('penerima', 'semua')
    if kategori not in dict(Pengumuman.KATEGORI):
        err.append('Pilih kategori pesan.')
    if len(judul) < 4:
        err.append('Judul minimal 4 karakter.')
    if len(isi) < 10:
        err.append('Isi pesan masih kosong.')
    if len(isi) > MAKS_ISI:
        err.append(f'Isi pesan maksimal {MAKS_ISI} karakter.')
    if penerima not in dict(Pengumuman.PENERIMA):
        err.append('Penerima tidak valid.')
    ids = [int(x) for x in data.getlist('tenants') if x.isdigit()]
    tenants = list(Tenant.objects.filter(pk__in=ids))
    if penerima == 'pilih' and not tenants:
        err.append('Pilih minimal satu cafe penerima.')
    berlaku = None
    if data.get('berlaku_sampai'):
        berlaku = parse_datetime(data['berlaku_sampai'])
        if berlaku is None:
            err.append('Format tanggal tampil sampai tidak valid.')
        elif timezone.is_naive(berlaku):
            berlaku = timezone.make_aware(berlaku)
    berkas = request.FILES.get('lampiran')
    if berkas:
        head = berkas.read(5)
        berkas.seek(0)
        if berkas.size > MAKS_LAMPIRAN or head != b'%PDF-':
            err.append('Lampiran harus file PDF yang valid, maksimal 5 MB.')
    if err:
        return err

    p.kategori, p.judul, p.isi, p.penerima = kategori, judul, isi, penerima
    p.tampil_banner = data.get('tampil_banner') == 'on'
    p.berlaku_sampai = berlaku or (timezone.now() + timedelta(days=3) if p.tampil_banner else None)
    p.dibuat_oleh = p.dibuat_oleh or request.user.get_username()
    if data.get('hapus_lampiran') == '1' and p.lampiran:
        p.lampiran.delete(save=False)
    if berkas:
        if p.lampiran:
            p.lampiran.delete(save=False)
        p.lampiran.save('lampiran.pdf', berkas, save=False)
    p.save()
    if not p.nomor:
        p.nomor = buat_nomor(p)
        p.save(update_fields=['nomor'])
    p.tenants.set(tenants if penerima == 'pilih' else [])
    return []


@panel_required
def panel_pengumuman_form(request, pk=None):
    p = get_object_or_404(Pengumuman, pk=pk) if pk else Pengumuman()
    if request.method == 'POST':
        err = _simpan(request, p)
        if not err:
            messages.success(request, 'Pesan tersimpan dan sudah tampil di dasbor cafe penerima.')
            return redirect('panel_pengumuman_detail', pk=p.pk)
        for e in err:
            messages.error(request, e)
        p.judul, p.isi = request.POST.get('judul', '')[:150], request.POST.get('isi', '')[:MAKS_ISI]
        if request.POST.get('kategori') in dict(Pengumuman.KATEGORI):
            p.kategori = request.POST['kategori']
    return render(request, 'panel/pengumuman_form.html', {
        'active': 'pengumuman', 'p': p, 'templat': TEMPLAT, 'kategori': Pengumuman.KATEGORI,
        'cafes': Tenant.objects.order_by('nama_cafe'), 'dipilih': set(p.tenants.values_list('pk', flat=True)) if p.pk else set(),
        'isian': ISIAN, 'maks_isi': MAKS_ISI,
    })


@panel_required
def panel_pengumuman_detail(request, pk):
    p = get_object_or_404(Pengumuman, pk=pk)
    cafes = Tenant.objects.order_by('nama_cafe') if p.penerima == 'semua' else p.tenants.order_by('nama_cafe')
    baca = dict(p.dibaca.values_list('tenant_id', 'waktu'))
    contoh = cafes.first()
    ctx = _konteks_surat(p, contoh, 'admin', '/panel/pengumuman/')
    ctx.update({'status_baca': [{'t': t, 'waktu': baca.get(t.pk)} for t in cafes]})
    return render(request, 'pengumuman/surat.html', ctx)


@panel_required
@require_POST
def panel_pengumuman_hapus(request, pk):
    p = get_object_or_404(Pengumuman, pk=pk)
    if p.lampiran:
        p.lampiran.delete(save=False)
    p.delete()
    messages.success(request, 'Pesan dihapus dari semua dasbor cafe.')
    return redirect('panel_pengumuman')


def _tenant_owner(request, tenant_slug):
    tenant = get_object_or_404(Tenant, slug=tenant_slug)
    prof = getattr(request.user, 'profile', None)
    return tenant, bool(prof and prof.tenant_id == tenant.id and prof.role == 'owner')


@login_required(login_url='/login/')
def owner_pesan(request, tenant_slug, pk):
    tenant, ok = _tenant_owner(request, tenant_slug)
    if not ok:
        return render(request, 'forbidden.html', {'pesan': 'Hanya owner cafe ini yang dapat membuka pesan.'}, status=403)
    p = get_object_or_404(untuk_cafe(tenant), pk=pk)
    tandai_dibaca(p, tenant)
    return render(request, 'pengumuman/surat.html', _konteks_surat(p, tenant, 'owner', f'/{tenant.slug}/owner/#berkas'))


@login_required(login_url='/login/')
def pesan_lampiran(request, pk):
    p = get_object_or_404(Pengumuman, pk=pk)
    if not p.lampiran:
        raise Http404
    if not request.user.is_staff:
        prof = getattr(request.user, 'profile', None)
        if not prof or prof.role != 'owner' or not untuk_cafe(prof.tenant).filter(pk=p.pk).exists():
            raise Http404
    return FileResponse(p.lampiran.open('rb'), as_attachment=True, filename=f'Lampiran-{p.pk}.pdf')
