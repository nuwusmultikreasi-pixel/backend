import io
from datetime import date

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from .billing import hitung_denda
from .models import Invoice, Menu, Tenant, UserProfile
from .uploads import bersihkan_gambar


def gambar(nama='a.png', fmt='PNG', ukuran=(60, 60)):
    buf = io.BytesIO()
    Image.new('RGB', ukuran, (11, 29, 56)).save(buf, fmt)
    return SimpleUploadedFile(nama, buf.getvalue(), content_type=f'image/{fmt.lower()}')


def buat_cafe(slug):
    t = Tenant.objects.create(nama_cafe=slug.title(), slug=slug, nama_owner='Pemilik', email_owner=f'{slug}@contoh.id',
                              whatsapp='081234567890', alamat='Malang')
    menu = Menu.objects.create(tenant=t, nama_menu='Kopi', harga=10000)
    return t, menu


class DendaTests(TestCase):
    def setUp(self):
        self.inv = Invoice(total=200000, jatuh_tempo=date(2026, 11, 30), status='unpaid')

    def test_tanpa_denda_selama_masa_tenggang(self):
        self.assertEqual(hitung_denda(self.inv, date(2026, 11, 30)), 0)
        self.assertEqual(hitung_denda(self.inv, date(2026, 12, 3)), 0)

    def test_denda_per_hari_setelah_tenggang(self):
        self.assertEqual(hitung_denda(self.inv, date(2026, 12, 4)), 200)
        self.assertEqual(hitung_denda(self.inv, date(2026, 12, 23)), 4000)

    def test_denda_dibatasi_maksimal(self):
        self.assertEqual(hitung_denda(self.inv, date(2027, 12, 31)), 20000)

    def test_invoice_lunas_memakai_denda_tersimpan(self):
        self.inv.status, self.inv.denda = 'paid', 1234
        self.assertEqual(hitung_denda(self.inv, date(2027, 1, 1)), 1234)


class UploadTests(TestCase):
    def test_gambar_valid_ditulis_ulang_dengan_nama_acak(self):
        hasil = bersihkan_gambar(gambar('logo saya.png'), 'Logo')
        self.assertTrue(hasil.name.endswith('.png'))
        self.assertNotIn('logo', hasil.name)

    def test_file_palsu_berekstensi_gambar_ditolak(self):
        palsu = SimpleUploadedFile('shell.png', b'<?php echo 1; ?>', content_type='image/png')
        with self.assertRaises(ValidationError):
            bersihkan_gambar(palsu, 'Logo')

    def test_ukuran_berlebih_ditolak(self):
        with self.assertRaises(ValidationError):
            bersihkan_gambar(gambar(), 'Logo', maks_mb=0)

    def test_format_selain_png_jpg_webp_ditolak(self):
        with self.assertRaises(ValidationError):
            bersihkan_gambar(gambar('a.gif', 'GIF'), 'Logo')


class OrderAksesTests(TestCase):
    def setUp(self):
        cache.clear()
        self.t, self.menu = buat_cafe('kopi-a')
        self.t2, self.menu2 = buat_cafe('kopi-b')

    def pesan(self, **extra):
        data = {'tenant': self.t.id, 'nama_pemesan': 'Ani', 'nomor_meja': '1', 'metode_pembayaran': 'QRIS',
                'items': [{'menu': self.menu.id, 'jumlah': 2}], **extra}
        return self.client.post('/api/order/', data, content_type='application/json')

    def test_total_dihitung_server_termasuk_biaya_layanan(self):
        r = self.pesan(total_harga=1)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()['total_harga'], 20000 + r.json()['biaya_layanan'])

    def test_pesanan_tidak_bisa_dibuka_tanpa_token(self):
        oid = self.pesan().json()['id']
        self.assertIn(self.client.get(f'/api/order/{oid}/').status_code, (403, 404))

    def test_pesanan_bisa_dibuka_dengan_token(self):
        data = self.pesan().json()
        r = self.client.get(f"/api/order/{data['id']}/", HTTP_X_ORDER_TOKEN=data['akses_token'])
        self.assertEqual(r.status_code, 200)

    def test_menu_cafe_lain_ditolak(self):
        self.assertEqual(self.pesan(items=[{'menu': self.menu2.id, 'jumlah': 1}]).status_code, 400)

    def test_jumlah_tidak_wajar_ditolak(self):
        self.assertEqual(self.pesan(items=[{'menu': self.menu.id, 'jumlah': 1000}]).status_code, 400)

    def test_kasir_tidak_bisa_melihat_pesanan_cafe_lain(self):
        oid = self.pesan().json()['id']
        kasir = User.objects.create_user('kasir.b', password='Rahasia#2026')
        UserProfile.objects.create(user=kasir, tenant=self.t2, role='kasir')
        self.client.force_login(kasir)
        self.assertEqual(self.client.get(f'/api/order/{oid}/').status_code, 404)
        self.assertFalse(any(o['id'] == oid for o in self.client.get('/api/order/').json()))


@override_settings(DINEZY_LOGIN_MAKS_GAGAL=3)
class LoginGuardTests(TestCase):
    def setUp(self):
        cache.clear()
        self.t, _ = buat_cafe('kopi-c')
        self.user = User.objects.create_user('owner.c', password='Rahasia#2026')
        UserProfile.objects.create(user=self.user, tenant=self.t, role='owner')

    def tearDown(self):
        cache.clear()

    def test_dikunci_setelah_gagal_berulang(self):
        for i in range(3):
            self.client.post('/login/', {'username': 'owner.c', 'password': f'salah{i}'})
        r = self.client.post('/login/', {'username': 'owner.c', 'password': 'Rahasia#2026'}, follow=True)
        self.assertContains(r, 'Terlalu banyak percobaan')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_benar_berhasil(self):
        r = self.client.post('/login/', {'username': 'owner.c', 'password': 'Rahasia#2026'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, f'/{self.t.slug}/owner/')


class HeaderKeamananTests(TestCase):
    def test_header_keamanan(self):
        r = self.client.get('/')
        self.assertIn("frame-ancestors 'self'", r.headers['Content-Security-Policy'])
        self.assertEqual(r.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(r.headers['X-Frame-Options'], 'SAMEORIGIN')
        self.assertIn('camera=()', r.headers['Permissions-Policy'])

    def test_halaman_login_tidak_disimpan_cache(self):
        self.assertIn('no-store', self.client.get('/login/').headers.get('Cache-Control', ''))

    def test_dokumen_perjanjian_tidak_publik(self):
        self.assertEqual(self.client.get('/media/perjanjian/1/a.png').status_code, 404)


class PengumumanTests(TestCase):
    def setUp(self):
        cache.clear()
        self.a, _ = buat_cafe('kopi-d')
        self.b, _ = buat_cafe('kopi-e')
        self.owner_a = User.objects.create_user('owner.d', password='Rahasia#2026')
        UserProfile.objects.create(user=self.owner_a, tenant=self.a, role='owner')
        self.admin = User.objects.create_user('admin.dinezy', password='Rahasia#2026', is_staff=True)

    def kirim(self, **data):
        self.client.force_login(self.admin)
        base = {'kategori': 'surat', 'judul': 'Uji pesan', 'isi': 'Halo {nama_cafe}, ini isi pesan.', 'penerima': 'semua'}
        r = self.client.post('/panel/pengumuman/baru/', {**base, **data})
        self.client.logout()
        return r

    def test_admin_mengirim_dan_owner_membaca(self):
        self.kirim()
        from .models import Pengumuman
        p = Pengumuman.objects.get()
        self.assertTrue(p.nomor.endswith('/2026') or '/SRT/' in p.nomor)
        self.client.force_login(self.owner_a)
        r = self.client.get(f'/{self.a.slug}/owner/pesan/{p.pk}/')
        self.assertContains(r, f'Halo {self.a.nama_cafe}')
        self.assertTrue(p.dibaca.filter(tenant=self.a).exists())

    def test_isi_pesan_di_escape(self):
        self.kirim(isi='<script>alert(1)</script> isi panjang')
        from .models import Pengumuman
        p = Pengumuman.objects.get()
        self.client.force_login(self.owner_a)
        r = self.client.get(f'/{self.a.slug}/owner/pesan/{p.pk}/')
        self.assertNotContains(r, '<script>alert(1)</script>')
        self.assertContains(r, '&lt;script&gt;')

    def test_pesan_khusus_tidak_bisa_dibuka_cafe_lain(self):
        self.kirim(penerima='pilih', tenants=[self.b.pk])
        from .models import Pengumuman
        p = Pengumuman.objects.get()
        self.client.force_login(self.owner_a)
        self.assertEqual(self.client.get(f'/{self.a.slug}/owner/pesan/{p.pk}/').status_code, 404)
        self.assertEqual(self.client.get(f'/{self.b.slug}/owner/pesan/{p.pk}/').status_code, 403)

    def test_owner_tidak_bisa_masuk_panel_admin(self):
        self.client.force_login(self.owner_a)
        r = self.client.get('/panel/pengumuman/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login/', r.url)


class SeranganUmumTests(TestCase):
    def setUp(self):
        cache.clear()
        self.t, self.menu = buat_cafe('kopi-f')

    def test_csrf_wajib_untuk_form(self):
        from django.test import Client
        c = Client(enforce_csrf_checks=True)
        self.assertEqual(c.post('/login/', {'username': 'x', 'password': 'y'}).status_code, 403)

    def test_parameter_sql_injection_tidak_bocor(self):
        r = self.client.get('/api/menu/', {'tenant': '1 OR 1=1'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [])
        r = self.client.get('/api/menu/', {'tenant_slug': "x' OR '1'='1"})
        self.assertEqual(r.json(), [])

    def test_path_traversal_media(self):
        for url in ('/media/../config/settings.py', '/media/..%2Fconfig%2Fsettings.py', '/media/x/../../manage.py'):
            self.assertIn(self.client.get(url).status_code, (400, 404))

    def test_login_admin_django_diarahkan_ke_login_terlindungi(self):
        r = self.client.get('/admin/login/')
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.url.startswith('/login/?mode=admin'))

    def test_open_redirect_ditolak(self):
        r = self.client.get('/admin/login/', {'next': 'https://evil.example/'})
        self.assertNotIn('evil', r.url)

    def test_honeypot_pendaftaran(self):
        r = self.client.post('/daftar/', {'website': 'http://spam', 'nama_cafe': 'Spam'})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Tenant.objects.filter(nama_cafe='Spam').exists())

    @override_settings(DINEZY_DAFTAR_MAKS_PER_JAM=2)
    def test_batas_pendaftaran_per_ip(self):
        for _ in range(3):
            r = self.client.post('/daftar/', {'nama_cafe': ''}, follow=True)
        self.assertContains(r, 'Terlalu banyak percobaan pendaftaran')

    def test_anonim_tidak_bisa_mengubah_data(self):
        self.assertIn(self.client.delete(f'/api/menu/{self.menu.pk}/').status_code, (401, 403))
        self.assertIn(self.client.post('/api/meja/', {'nomor_meja': '1'}).status_code, (401, 403))
        self.assertIn(self.client.patch(f'/api/tenant/{self.t.slug}/', {'nama_cafe': 'x'},
                                        content_type='application/json').status_code, (401, 403))
