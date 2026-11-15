from datetime import timedelta

from django.conf import settings
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from .billing import tarif
from .models import Pengumuman, PengumumanBaca
from .perjanjian import ROMAWI, tanggal_panjang

MAKS_ISI = 8000
KATEGORI_FORMAL = ('pks', 'surat', 'tagihan')
IKON = {
    'maintenance': 'fa-screwdriver-wrench', 'gangguan': 'fa-triangle-exclamation', 'pembaruan': 'fa-wand-magic-sparkles',
    'pks': 'fa-file-signature', 'tagihan': 'fa-file-invoice-dollar', 'surat': 'fa-envelope-open-text', 'info': 'fa-circle-info',
}
WARNA = {
    'maintenance': 'amber', 'gangguan': 'red', 'pembaruan': 'blue', 'pks': 'blue', 'tagihan': 'amber',
    'surat': 'gray', 'info': 'gray',
}

TEMPLAT = [
    {
        'kode': 'maintenance', 'nama': 'Pemeliharaan terjadwal', 'kategori': 'maintenance', 'banner': True,
        'judul': 'Pemeliharaan Sistem Terjadwal',
        'isi': (
            'Yth. Pemilik {nama_cafe},\n\n'
            'Kami akan melakukan pemeliharaan sistem Dinezy pada:\n\n'
            'Hari/tanggal : [isi hari dan tanggal]\n'
            'Waktu        : [jam mulai] sampai [jam selesai] WIB\n\n'
            'Selama pemeliharaan, halaman menu pelanggan, dasbor kasir, dan dasbor owner tidak dapat diakses. '
            'Pesanan yang masuk sebelum pemeliharaan tetap tersimpan dengan aman.\n\n'
            'Selama jam tersebut, kami sarankan pesanan dicatat langsung di kasir. '
            'Mohon maaf atas ketidaknyamanannya dan terima kasih atas pengertian Anda.'
        ),
    },
    {
        'kode': 'gangguan', 'nama': 'Gangguan sedang ditangani', 'kategori': 'gangguan', 'banner': True,
        'judul': 'Gangguan Layanan Sedang Ditangani',
        'isi': (
            'Yth. Pemilik {nama_cafe},\n\n'
            'Sejak pukul [jam] WIB hari ini, sebagian pengguna mengalami kendala pada [bagian yang terganggu, '
            'misalnya pengiriman pesanan dari meja].\n\n'
            'Tim kami sedang menangani masalah ini. Sementara itu, pesanan dapat dicatat langsung di kasir.\n\n'
            'Kami akan memberi kabar kembali setelah layanan pulih.'
        ),
    },
    {
        'kode': 'pulih', 'nama': 'Layanan sudah pulih', 'kategori': 'gangguan', 'banner': False,
        'judul': 'Layanan Telah Kembali Normal',
        'isi': (
            'Yth. Pemilik {nama_cafe},\n\n'
            'Gangguan pada [bagian yang terganggu] pada [tanggal], pukul [jam mulai] sampai [jam selesai] WIB, '
            'sudah selesai ditangani. Layanan kembali berjalan normal.\n\n'
            'Apabila masih menemukan kendala, silakan hubungi kami melalui WhatsApp {wa_admin}.\n\n'
            'Terima kasih atas kesabaran Anda.'
        ),
    },
    {
        'kode': 'pembaruan', 'nama': 'Pembaruan aplikasi', 'kategori': 'pembaruan', 'banner': False,
        'judul': 'Pembaruan Aplikasi Dinezy',
        'isi': (
            'Yth. Pemilik {nama_cafe},\n\n'
            'Mulai [tanggal], Dinezy mendapat pembaruan berikut:\n\n'
            '1. [fitur atau perbaikan pertama]\n'
            '2. [fitur atau perbaikan kedua]\n\n'
            'Pembaruan berlaku otomatis dan tidak perlu dipasang. '
            'Jika ada pertanyaan, hubungi kami melalui WhatsApp {wa_admin}.'
        ),
    },
    {
        'kode': 'pks', 'nama': 'Pembaruan PKS / S&K', 'kategori': 'pks', 'banner': True,
        'judul': 'Pemberitahuan Pembaruan Perjanjian Kerja Sama',
        'isi': (
            'Dengan hormat,\n\n'
            'Bersama surat ini kami memberitahukan bahwa Perjanjian Kerja Sama dan Syarat & Ketentuan Layanan '
            'Dinezy diperbarui ke versi [nomor versi] dan berlaku mulai [tanggal berlaku].\n\n'
            'Pokok perubahan:\n'
            '1. [ringkasan perubahan pertama]\n'
            '2. [ringkasan perubahan kedua]\n\n'
            'Dokumen lengkap dapat dibaca melalui menu Berkas & Pesan pada dasbor owner. Apabila Bapak/Ibu '
            'memiliki keberatan, mohon disampaikan kepada kami sebelum tanggal berlaku.\n\n'
            'Atas perhatian dan kerja sama Bapak/Ibu, kami ucapkan terima kasih.'
        ),
    },
    {
        'kode': 'tarif', 'nama': 'Penyesuaian biaya layanan', 'kategori': 'pks', 'banner': True,
        'judul': 'Pemberitahuan Penyesuaian Biaya Layanan',
        'isi': (
            'Dengan hormat,\n\n'
            'Sesuai Pasal 5 ayat (3) dan ayat (4) Perjanjian Kerja Sama, kami memberitahukan penyesuaian '
            'Biaya Layanan Dinezy sebagai berikut:\n\n'
            'Biaya saat ini : Rp{tarif} per nota\n'
            'Biaya baru     : Rp[nominal baru] per nota\n'
            'Berlaku mulai  : [tanggal, paling cepat 30 hari setelah surat ini]\n\n'
            'Biaya baru tidak berlaku surut terhadap nota yang telah terbit. Apabila Bapak/Ibu tidak menyetujui '
            'penyesuaian ini, Perjanjian dapat diakhiri sebelum tanggal berlaku tanpa denda sesuai Pasal 5 ayat (6).\n\n'
            'Terima kasih atas kepercayaan Bapak/Ibu menggunakan Dinezy.'
        ),
    },
    {
        'kode': 'tagihan', 'nama': 'Pengingat tagihan', 'kategori': 'tagihan', 'banner': False,
        'judul': 'Pengingat Pembayaran Tagihan Layanan',
        'isi': (
            'Yth. Pemilik {nama_cafe},\n\n'
            'Kami mengingatkan bahwa tagihan layanan periode [bulan dan tahun] sebesar Rp[jumlah] '
            'jatuh tempo pada [tanggal jatuh tempo].\n\n'
            'Invoice dapat dilihat pada menu Tagihan di dasbor owner. Pembayaran yang melewati masa tenggang '
            '3 hari setelah jatuh tempo dikenakan denda keterlambatan sesuai Pasal 6 Perjanjian Kerja Sama, '
            'dan akses aplikasi dapat ditangguhkan sementara.\n\n'
            'Mohon abaikan pesan ini apabila pembayaran sudah dilakukan.'
        ),
    },
    {
        'kode': 'surat', 'nama': 'Surat resmi (kosong)', 'kategori': 'surat', 'banner': False,
        'judul': '[Perihal surat]',
        'isi': (
            'Dengan hormat,\n\n'
            '[Isi surat]\n\n'
            'Demikian surat ini kami sampaikan. Atas perhatian Bapak/Ibu, kami ucapkan terima kasih.'
        ),
    },
]

ISIAN = '{nama_cafe}, {nama_owner}, {tarif}, {wa_admin}, {tanggal}'


def _rupiah(n):
    return f'{n:,}'.replace(',', '.')


def isi_untuk(p, tenant=None):
    nilai = {
        '{nama_cafe}': tenant.nama_cafe if tenant else '[nama cafe]',
        '{nama_owner}': tenant.nama_owner if tenant else '[nama pemilik]',
        '{tarif}': _rupiah(tarif(tenant)),
        '{wa_admin}': getattr(settings, 'DINEZY_PERUSAHAAN_WA', ''),
        '{tanggal}': tanggal_panjang(p.dibuat or timezone.now()).split(', ', 1)[-1],
    }
    teks = p.isi
    for k, v in nilai.items():
        teks = teks.replace(k, v)
    return teks


def buat_nomor(p):
    t = timezone.localtime(p.dibuat)
    kode = 'SRT' if p.kategori in KATEGORI_FORMAL else 'INFO'
    return f'{p.pk:03d}/{kode}/DNZ-NM/{ROMAWI[t.month]}/{t.year}'


def untuk_cafe(tenant):
    batas = (tenant.created_at or timezone.now()) - timedelta(days=30)
    dibaca = PengumumanBaca.objects.filter(pengumuman=OuterRef('pk'), tenant=tenant)
    return (Pengumuman.objects
            .filter(Q(penerima='semua', dibuat__gte=batas) | Q(penerima='pilih', tenants=tenant))
            .distinct()
            .annotate(sudah_dibaca=Exists(dibaca)))


def jumlah_belum_dibaca(tenant):
    return untuk_cafe(tenant).filter(sudah_dibaca=False).count()


def banner_aktif(tenant):
    now = timezone.now()
    return (untuk_cafe(tenant)
            .filter(tampil_banner=True)
            .filter(Q(berlaku_sampai__isnull=True) | Q(berlaku_sampai__gt=now))
            .first())


def tandai_dibaca(p, tenant):
    PengumumanBaca.objects.get_or_create(pengumuman=p, tenant=tenant)
