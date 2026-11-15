import base64
import binascii
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST

from .billing import tarif, tarif_standar
from .models import Perjanjian, Tenant
from .panel import panel_required
from .security import client_ip
from .perjanjian import (BERLAKU_SEJAK, VERSI, batas_hari, batas_ttd, get_pks, hash_isi, perusahaan,
                         ketentuan_denda, tanggal_panjang, terbilang, ttd_data_uri)

MAKS_TTD = 400 * 1024
MAKS_FINAL = 10 * 1024 * 1024


def _ip(request):
    return client_ip(request)[:45]


def _konteks_pks(pks, request=None):
    t = pks.tenant
    nominal = pks.tarif_saat_ttd if pks.tarif_saat_ttd is not None else tarif(t)
    tgl = pks.ttd_at or timezone.now()
    return {
        'pks': pks, 't': t, 'p1': perusahaan(),
        'tarif': nominal, 'tarif_kata': terbilang(nominal), 'tarif_standar': tarif_standar(),
        'tanggal': tanggal_panjang(tgl), 'tgl': timezone.localtime(tgl),
        'ttd_p2': ttd_data_uri(pks), 'batas': batas_ttd(pks), 'batas_hari': batas_hari(),
        'versi': pks.versi or VERSI,
        **ketentuan_denda(),
    }


def _isi_pks(pks):
    return render_to_string('perjanjian/_isi_pks.html', _konteks_pks(pks))


def syarat_view(request):
    return render(request, 'perjanjian/syarat.html', {
        'p1': perusahaan(), 'versi': VERSI, 'berlaku': BERLAKU_SEJAK,
        'tarif': tarif_standar(), 'tarif_kata': terbilang(tarif_standar()), **ketentuan_denda(),
    })


def _owner_tenant(request, tenant_slug):
    tenant = get_object_or_404(Tenant, slug=tenant_slug)
    prof = getattr(request.user, 'profile', None)
    if not prof or prof.tenant_id != tenant.id or prof.role != 'owner':
        return tenant, False
    return tenant, True


@login_required(login_url='/login/')
def owner_perjanjian(request, tenant_slug):
    tenant, ok = _owner_tenant(request, tenant_slug)
    if not ok:
        return render(request, 'forbidden.html', {'pesan': 'Hanya owner cafe ini yang dapat membuka perjanjian.'}, status=403)
    pks = get_pks(tenant)

    if request.method == 'POST':
        if pks.sudah_ttd:
            messages.info(request, 'Perjanjian ini sudah ditandatangani.')
            return redirect('owner_perjanjian', tenant_slug=tenant.slug)
        nama = ' '.join((request.POST.get('nama') or '').split())[:120]
        data = request.POST.get('ttd') or ''
        err = []
        if len(nama) < 3:
            err.append('Tulis nama lengkap penanda tangan.')
        if request.POST.get('setuju') != 'on':
            err.append('Centang pernyataan persetujuan terlebih dahulu.')
        png = b''
        if not data.startswith('data:image/png;base64,'):
            err.append('Tanda tangan belum dibuat.')
        else:
            try:
                png = base64.b64decode(data.split(',', 1)[1], validate=True)
            except (binascii.Error, ValueError):
                png = b''
            if not png.startswith(b'\x89PNG') or len(png) < 800:
                err.append('Tanda tangan tidak terbaca. Silakan ulangi.')
            elif len(png) > MAKS_TTD:
                err.append('Ukuran gambar tanda tangan terlalu besar.')
        if err:
            for e in err:
                messages.error(request, e)
            return redirect('owner_perjanjian', tenant_slug=tenant.slug)

        now = timezone.now()
        pks.nama_penandatangan = nama
        pks.jabatan_penandatangan = 'Pemilik'
        pks.tarif_saat_ttd = tarif(tenant)
        pks.ttd_at, pks.ttd_ip = now, _ip(request)
        pks.ttd_perangkat = (request.META.get('HTTP_USER_AGENT') or '')[:255]
        pks.ttd.save('ttd.png', ContentFile(png), save=False)
        pks.status = 'ditandatangani'
        if not pks.sk_disetujui_at:
            pks.sk_disetujui_at, pks.sk_ip = now, pks.ttd_ip
        pks.versi = pks.versi or VERSI
        pks.save()
        pks.kode_dokumen = hash_isi(_isi_pks(pks))
        pks.save(update_fields=['kode_dokumen'])
        messages.success(request, 'Perjanjian Kerja Sama berhasil ditandatangani. Terima kasih!')
        if request.session.pop('register_result', None):
            request.session['dz_splash'] = {'nama': nama[:40], 'cafe': tenant.nama_cafe}
            return redirect('owner_dashboard', tenant_slug=tenant.slug)
        return redirect('owner_perjanjian', tenant_slug=tenant.slug)

    ctx = _konteks_pks(pks)
    ctx.update({'mode': 'owner', 'kembali': f'/{tenant.slug}/owner/',
                'baru': request.session.get('register_result') if not pks.sudah_ttd else None})
    return render(request, 'perjanjian/pks.html', ctx)


@login_required(login_url='/login/')
def unduh_final(request, pk):
    pks = get_object_or_404(Perjanjian, pk=pk)
    prof = getattr(request.user, 'profile', None)
    boleh = request.user.is_staff or (prof and prof.tenant_id == pks.tenant_id and prof.role == 'owner')
    if not boleh:
        raise Http404
    if not pks.file_final:
        raise Http404
    ext = os.path.splitext(pks.file_final.name)[1] or '.pdf'
    nama = f"PKS-{pks.tenant.slug}{ext}"
    return FileResponse(pks.file_final.open('rb'), as_attachment=True, filename=nama)


@panel_required
def panel_perjanjian(request):
    for t in Tenant.objects.filter(perjanjian__isnull=True):
        get_pks(t)
    f = request.GET.get('status', '')
    qs = Perjanjian.objects.select_related('tenant').order_by('status', '-dibuat')
    if f in dict(Perjanjian.STATUS):
        qs = qs.filter(status=f)
    hitung = {k: Perjanjian.objects.filter(status=k).count() for k, _ in Perjanjian.STATUS}
    rows = [{'p': p, 'batas': batas_ttd(p), 'lewat': p.status == 'menunggu' and timezone.localdate() > batas_ttd(p)}
            for p in qs]
    return render(request, 'panel/perjanjian.html', {'active': 'perjanjian', 'rows': rows, 'f': f, 'hitung': hitung,
                                                     'status_list': Perjanjian.STATUS})


@panel_required
def panel_perjanjian_detail(request, pk):
    pks = get_object_or_404(Perjanjian.objects.select_related('tenant'), pk=pk)
    ctx = _konteks_pks(pks)
    ctx.update({'mode': 'admin', 'kembali': '/panel/perjanjian/'})
    return render(request, 'perjanjian/pks.html', ctx)


@panel_required
@require_POST
def panel_perjanjian_unggah(request, pk):
    pks = get_object_or_404(Perjanjian, pk=pk)
    f = request.FILES.get('file_final')
    if not pks.sudah_ttd:
        messages.error(request, 'PKS belum ditandatangani PIHAK KEDUA.')
    elif not f:
        messages.error(request, 'Pilih file PDF yang sudah dibubuhi e-meterai.')
    elif not f.name.lower().endswith('.pdf') or f.size > MAKS_FINAL:
        messages.error(request, 'File harus PDF dan maksimal 10 MB.')
    else:
        head = f.read(5); f.seek(0)
        if head != b'%PDF-':
            messages.error(request, 'File bukan PDF yang valid.')
        else:
            if pks.file_final:
                pks.file_final.delete(save=False)
            pks.file_final.save('final.pdf', f, save=False)
            pks.final_at, pks.final_oleh, pks.status = timezone.now(), request.user.get_username(), 'bermeterai'
            pks.save()
            messages.success(request, f'PKS final bermeterai untuk {pks.tenant.nama_cafe} tersimpan. Owner sudah dapat mengunduhnya.')
    return redirect('panel_perjanjian_detail', pk=pks.pk)
