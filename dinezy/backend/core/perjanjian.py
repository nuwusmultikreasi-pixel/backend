import base64
import hashlib
from datetime import timedelta

from django.conf import settings
from django.contrib.staticfiles import finders
from django.utils import timezone

from .models import Perjanjian

VERSI = '1.1'
BERLAKU_SEJAK = '14 November 2026'
ROMAWI = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII']
HARI = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']


def perusahaan():
    g = lambda k, d: getattr(settings, k, d) or d
    return {
        'nama': g('DINEZY_PERUSAHAAN_NAMA', 'PT NUWUS MULTIKREASI DIGITAL'),
        'alamat': g('DINEZY_PERUSAHAAN_ALAMAT', '[alamat kantor]'),
        'sk': g('DINEZY_PERUSAHAAN_SK', ''),
        'nib': g('DINEZY_PERUSAHAAN_NIB', ''),
        'wakil': g('DINEZY_PERUSAHAAN_WAKIL', '[nama Direktur]'),
        'jabatan': g('DINEZY_PERUSAHAAN_JABATAN', 'Direktur'),
        'email': g('DINEZY_PERUSAHAAN_EMAIL', '[email resmi]'),
        'wa': g('DINEZY_PERUSAHAAN_WA', '[nomor WhatsApp resmi]'),
        'pengadilan': g('DINEZY_PENGADILAN', 'Pengadilan Negeri yang wilayah hukumnya meliputi domisili PIHAK PERTAMA'),
        'ttd': _data_uri_static('core/img/ttd-pihak-pertama.png'),
    }


def batas_hari():
    return int(getattr(settings, 'DINEZY_PKS_BATAS_HARI', 14) or 14)


def _data_uri_static(path):
    p = finders.find(path)
    if not p:
        return ''
    with open(p, 'rb') as f:
        return 'data:image/png;base64,' + base64.b64encode(f.read()).decode()


def ttd_data_uri(pks):
    if not pks.ttd:
        return ''
    try:
        with pks.ttd.open('rb') as f:
            return 'data:image/png;base64,' + base64.b64encode(f.read()).decode()
    except (OSError, ValueError):
        return ''


def get_pks(tenant, ip=''):
    pks, baru = Perjanjian.objects.get_or_create(tenant=tenant, defaults={'versi': VERSI})
    if baru or not pks.nomor:
        t = timezone.localtime(pks.dibuat)
        pks.nomor = f"{pks.pk:03d}/PKS/DNZ-NM/{ROMAWI[t.month]}/{t.year}"
        pks.save(update_fields=['nomor'])
    return pks


def catat_persetujuan_sk(tenant, ip):
    pks = get_pks(tenant)
    pks.sk_disetujui_at, pks.sk_ip, pks.versi = timezone.now(), ip[:45], VERSI
    pks.save(update_fields=['sk_disetujui_at', 'sk_ip', 'versi'])
    return pks


def batas_ttd(pks):
    return timezone.localtime(pks.dibuat).date() + timedelta(days=batas_hari())


def hash_isi(teks):
    return hashlib.sha256(' '.join(teks.split()).encode('utf-8')).hexdigest()


def tanggal_panjang(dt):
    from .models import BULAN_ID
    d = timezone.localtime(dt) if hasattr(dt, 'tzinfo') and dt.tzinfo else dt
    return f"{HARI[d.weekday()]}, {d.day} {BULAN_ID[d.month]} {d.year}"


_SATUAN = ['', 'satu', 'dua', 'tiga', 'empat', 'lima', 'enam', 'tujuh', 'delapan', 'sembilan', 'sepuluh', 'sebelas']


def terbilang(n):
    n = int(n)
    if n < 0:
        return 'minus ' + terbilang(-n)
    if n < 12:
        return _SATUAN[n] if n else 'nol'
    if n < 20:
        return terbilang(n - 10) + ' belas'
    if n < 100:
        return (terbilang(n // 10) + ' puluh ' + (terbilang(n % 10) if n % 10 else '')).strip()
    if n < 200:
        return ('seratus ' + (terbilang(n - 100) if n - 100 else '')).strip()
    if n < 1000:
        return (terbilang(n // 100) + ' ratus ' + (terbilang(n % 100) if n % 100 else '')).strip()
    if n < 2000:
        return ('seribu ' + (terbilang(n - 1000) if n - 1000 else '')).strip()
    for besar, nama in ((10 ** 12, 'triliun'), (10 ** 9, 'miliar'), (10 ** 6, 'juta'), (1000, 'ribu')):
        if n >= besar:
            sisa = n % besar
            return (terbilang(n // besar) + f' {nama} ' + (terbilang(sisa) if sisa else '')).strip()
    return str(n)


def kata_angka(x):
    x = float(x)
    if x.is_integer():
        return terbilang(int(x))
    bulat, pecahan = f"{x:g}".split('.')
    return terbilang(int(bulat)) + ' koma ' + ' '.join(terbilang(int(d)) for d in pecahan)


def ketentuan_denda():
    from .billing import aturan_denda
    a = aturan_denda()
    teks = lambda v: f"{v:g}".replace('.', ',')
    return {
        'denda': {**a, 'permil_teks': teks(a['permil']), 'maks_teks': teks(a['maks'])},
        'denda_permil_kata': kata_angka(a['permil']),
        'denda_maks_kata': kata_angka(a['maks']),
        'denda_tenggang_kata': terbilang(a['tenggang']),
    }
