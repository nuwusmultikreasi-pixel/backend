import secrets

from django.contrib.auth.models import User
from django.db import models


def token_pesanan():
    return secrets.token_urlsafe(32)


class Tenant(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    nama_cafe = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    nama_owner = models.CharField(max_length=100)
    email_owner = models.EmailField()
    whatsapp = models.CharField(max_length=20)
    alamat = models.TextField()
    logo = models.ImageField(upload_to='tenant_logos/', blank=True, null=True)
    
    qris_image = models.ImageField(upload_to='tenant_qris/', blank=True, null=True) 
    unpaid_bill = models.IntegerField(default=0)
    is_locked = models.BooleanField(default=False)
    LOCK_REASONS = [('', '-'), ('tagihan', 'Tagihan belum dibayar'), ('manual', 'Dikunci manual oleh admin')]
    tarif_layanan = models.PositiveIntegerField(null=True, blank=True, help_text='Biaya layanan per nota khusus cafe ini (Rp). Kosong = tarif standar.')
    tarif_diubah = models.DateTimeField(null=True, blank=True)
    lock_reason = models.CharField(max_length=10, choices=LOCK_REASONS, blank=True, default='')

    PRINT_TYPES = [('57', 'Printer thermal 57 x 30 mm'), ('58', 'Printer thermal 58 mm'), ('80', 'Printer thermal 80 mm'),
                   ('a5', 'Kertas A5 (printer biasa)'), ('a4', 'Kertas A4 (printer biasa)')]
    KITCHEN_PRINT = [('masuk', 'Otomatis saat pesanan masuk'), ('proses', 'Otomatis saat pesanan diproses kasir'),
                     ('off', 'Manual (tombol "Dapur")')]
    print_type = models.CharField(max_length=3, choices=PRINT_TYPES, default='80')
    kitchen_print = models.CharField(max_length=10, choices=KITCHEN_PRINT, default='masuk')
    nota_footer = models.CharField(max_length=120, blank=True, default='Terima kasih atas kunjungan Anda!')
    nota_show_qr = models.BooleanField(default=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nama_cafe


class Menu(models.Model):
    KATEGORI_CHOICES = [
        ('Makanan', 'Makanan'),
        ('Minuman', 'Minuman'),
        ('Snack', 'Snack'),
        ('Dessert', 'Dessert'),
        ('Lainnya', 'Lainnya'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='menus')
    nama_menu = models.CharField(max_length=100)
    deskripsi = models.CharField(max_length=255, blank=True, default='')
    kategori = models.CharField(max_length=20, choices=KATEGORI_CHOICES, default='Makanan')
    harga = models.IntegerField()
    foto = models.ImageField(upload_to='menu_photos/', blank=True, null=True)
    tersedia = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-tersedia', 'kategori', 'nama_menu']

    def __str__(self):
        return f"{self.nama_menu} - {self.tenant.nama_cafe}"


class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Belum Dibayar'),
        ('Menunggu', 'Menunggu Konfirmasi Kasir'),
        ('Diproses', 'Diproses Dapur'),
        ('Selesai', 'Selesai'),
    ]
    
    PAYMENT_CHOICES = [
        ('TUNAI', 'Tunai'),
        ('QRIS', 'QRIS'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='orders')
    nama_pemesan = models.CharField(max_length=100)
    nomor_meja = models.CharField(max_length=20)
    total_harga = models.IntegerField(default=0)
    biaya_layanan = models.IntegerField(default=0)

    metode_pembayaran = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='TUNAI')
    bukti_pembayaran = models.ImageField(upload_to='payment_proofs/', blank=True, null=True)
    
    status_pesanan = models.CharField(max_length=25, choices=STATUS_CHOICES, default='Pending')
    akses_token = models.CharField(max_length=43, default=token_pesanan, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def subtotal(self):
        return (self.total_harga or 0) - (self.biaya_layanan or 0)

    def __str__(self):
        return f"{self.nama_pemesan} - Meja {self.nomor_meja} ({self.tenant.nama_cafe})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE)
    jumlah = models.IntegerField(default=1)
    harga_satuan = models.IntegerField(default=0)
    catatan = models.CharField(max_length=150, blank=True, default='')

    def __str__(self):
        return f"{self.jumlah}x {self.menu.nama_menu}"


class Meja(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='meja_list')
    nomor_meja = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('tenant', 'nomor_meja')
        ordering = ['nomor_meja']

    def __str__(self):
        return f"{self.tenant.nama_cafe} - Meja {self.nomor_meja}"


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('kasir', 'Kasir'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='users', null=True, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='kasir')
    pw_enc = models.TextField(blank=True, default='')
    pw_set_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        tenant_name = self.tenant.nama_cafe if self.tenant else "Tanpa Tenant"
        return f"{self.user.username} - {self.role} ({tenant_name})"


BULAN_ID = ['', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli',
            'Agustus', 'September', 'Oktober', 'November', 'Desember']


class Invoice(models.Model):
    STATUS_CHOICES = [('unpaid', 'Belum Dibayar'), ('paid', 'Lunas')]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='invoices')
    tahun = models.PositiveIntegerField()
    bulan = models.PositiveSmallIntegerField()
    jumlah_nota = models.PositiveIntegerField(default=0)
    tarif = models.PositiveIntegerField(default=1500)
    total = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unpaid')
    tanggal_terbit = models.DateField()
    jatuh_tempo = models.DateField()
    dibayar_pada = models.DateTimeField(null=True, blank=True)
    denda = models.PositiveIntegerField(default=0)
    catatan = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('tenant', 'tahun', 'bulan')
        ordering = ['-tahun', '-bulan', 'tenant__nama_cafe']

    def __str__(self):
        return f"{self.nomor} - {self.tenant.nama_cafe}"

    @property
    def tarif_seragam(self):
        return self.total == self.jumlah_nota * self.tarif

    @property
    def nomor(self):
        return f"INV/{self.tahun}/{self.bulan:02d}/{self.tenant.slug.upper()}"

    @property
    def periode(self):
        return f"{BULAN_ID[self.bulan]} {self.tahun}"

    @property
    def denda_berjalan(self):
        from .billing import hitung_denda
        return hitung_denda(self)

    @property
    def hari_denda(self):
        from .billing import hari_denda
        return hari_denda(self)

    @property
    def total_bayar(self):
        return self.total + self.denda_berjalan

    @property
    def terlambat(self):
        from django.utils import timezone
        return self.status == 'unpaid' and timezone.localdate() > self.jatuh_tempo


def _pks_path(instance, filename):
    import os
    import uuid
    ext = os.path.splitext(filename)[1].lower() or '.bin'
    return f'perjanjian/{instance.tenant_id}/{uuid.uuid4().hex}{ext}'


class Perjanjian(models.Model):
    STATUS = [('menunggu', 'Menunggu tanda tangan'), ('ditandatangani', 'Sudah ditandatangani'),
              ('bermeterai', 'Final bermeterai')]

    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name='perjanjian')
    nomor = models.CharField(max_length=60, blank=True)
    versi = models.CharField(max_length=20, default='')
    status = models.CharField(max_length=20, choices=STATUS, default='menunggu')
    sk_disetujui_at = models.DateTimeField(null=True, blank=True)
    sk_ip = models.CharField(max_length=45, blank=True)
    nama_penandatangan = models.CharField(max_length=120, blank=True)
    jabatan_penandatangan = models.CharField(max_length=60, blank=True, default='Pemilik')
    tarif_saat_ttd = models.PositiveIntegerField(null=True, blank=True)
    ttd = models.FileField(upload_to=_pks_path, blank=True)
    ttd_at = models.DateTimeField(null=True, blank=True)
    ttd_ip = models.CharField(max_length=45, blank=True)
    ttd_perangkat = models.CharField(max_length=255, blank=True)
    kode_dokumen = models.CharField(max_length=64, blank=True)
    file_final = models.FileField(upload_to=_pks_path, blank=True)
    final_at = models.DateTimeField(null=True, blank=True)
    final_oleh = models.CharField(max_length=150, blank=True)
    dibuat = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Perjanjian Kerja Sama'
        verbose_name_plural = 'Perjanjian Kerja Sama'

    def __str__(self):
        return f"{self.nomor or 'PKS'} - {self.tenant.nama_cafe}"

    @property
    def sudah_ttd(self):
        return self.status in ('ditandatangani', 'bermeterai')


def _pengumuman_path(instance, filename):
    import uuid
    return f'pengumuman/{uuid.uuid4().hex}.pdf'


class Pengumuman(models.Model):
    KATEGORI = [
        ('maintenance', 'Pemeliharaan sistem'),
        ('gangguan', 'Gangguan layanan'),
        ('pembaruan', 'Pembaruan aplikasi'),
        ('pks', 'Perjanjian & ketentuan'),
        ('tagihan', 'Tagihan'),
        ('surat', 'Surat resmi'),
        ('info', 'Informasi'),
    ]
    PENERIMA = [('semua', 'Semua cafe'), ('pilih', 'Cafe tertentu')]

    nomor = models.CharField(max_length=60, blank=True, default='')
    kategori = models.CharField(max_length=20, choices=KATEGORI, default='info')
    judul = models.CharField(max_length=150)
    isi = models.TextField()
    penerima = models.CharField(max_length=10, choices=PENERIMA, default='semua')
    tenants = models.ManyToManyField(Tenant, blank=True, related_name='pengumuman_khusus')
    tampil_banner = models.BooleanField(default=False)
    berlaku_sampai = models.DateTimeField(null=True, blank=True)
    lampiran = models.FileField(upload_to=_pengumuman_path, blank=True, null=True)
    dibuat_oleh = models.CharField(max_length=150, blank=True, default='')
    dibuat = models.DateTimeField(auto_now_add=True)
    diubah = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-dibuat']

    def __str__(self):
        return self.judul


class PengumumanBaca(models.Model):
    pengumuman = models.ForeignKey(Pengumuman, on_delete=models.CASCADE, related_name='dibaca')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='pengumuman_dibaca')
    waktu = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('pengumuman', 'tenant')
