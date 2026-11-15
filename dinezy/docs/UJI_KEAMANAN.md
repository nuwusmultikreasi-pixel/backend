# Uji Keamanan Dinezy

Cara menjalankan seluruh pengujian otomatis:

```
python manage.py test core
```

Hasil terakhir: **31 pengujian lulus**.

## Pemetaan ke OWASP Top 10 (2021)

| Risiko OWASP | Perlindungan di aplikasi | Diuji oleh |
| --- | --- | --- |
| A01 Broken Access Control | Data owner/kasir dibatasi per cafe. Pesanan pelanggan hanya bisa dibuka dengan token rahasia. Pesan khusus hanya terbuka bagi cafe penerima. Panel admin khusus staf. | `OrderAksesTests`, `PengumumanTests`, `SeranganUmumTests.test_anonim_tidak_bisa_mengubah_data` |
| A02 Cryptographic Failures | Password di-hash PBKDF2 (bawaan Django). Salinan password untuk admin dienkripsi dan diberi HMAC. Cookie Secure + HSTS saat `DINEZY_HTTPS=1`. | `manage.py check --deploy` |
| A03 Injection | Seluruh query memakai ORM (parameterized). Parameter filter divalidasi. Isi template di-escape otomatis. | `test_parameter_sql_injection_tidak_bocor`, `test_isi_pesan_di_escape` |
| A04 Insecure Design | Total harga dihitung server, bukan dari browser. Batas jumlah item pesanan. Masa tenggang dan denda dihitung di server. | `test_total_dihitung_server_termasuk_biaya_layanan`, `DendaTests` |
| A05 Security Misconfiguration | Header CSP, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy. API browsable dimatikan di produksi. Login admin bawaan Django dialihkan ke login yang terlindungi. | `HeaderKeamananTests`, `test_login_admin_django_diarahkan_ke_login_terlindungi` |
| A06 Vulnerable Components | Versi minimum paket yang aman ditetapkan di `requirements.txt`. Jalankan `pip list --outdated` secara berkala. | - |
| A07 Identification & Authentication Failures | Login dikunci 15 menit setelah 5 kali gagal. Waktu respons disamakan untuk username yang tidak ada. Sesi berganti ID setiap login. | `LoginGuardTests` |
| A08 Software & Data Integrity | Kode verifikasi SHA-256 pada PKS. Lampiran hanya PDF yang valid. | `pks_test` |
| A09 Logging & Monitoring | Login gagal, pelanggaran batas permintaan, dan kegagalan CSRF dicatat di log `core.security` dan `django.security`. | - |
| A10 SSRF | Aplikasi tidak mengambil URL dari input pengguna. | - |

## Perlindungan tambahan

- **Unggahan gambar**: isi file diperiksa, ditulis ulang tanpa metadata, dan diberi nama acak. File palsu (misalnya skrip yang diberi nama `.png`) ditolak.
- **Berkas rahasia**: dokumen PKS dan lampiran surat tidak bisa diakses lewat URL publik. Hanya bisa diunduh lewat halaman yang memeriksa hak akses.
- **Formulir pendaftaran**: memakai honeypot anti-bot dan dibatasi 20 percobaan per jam per IP.
- **CSRF**: semua formulir wajib memakai token.
- **Open redirect**: parameter `next` hanya menerima alamat di domain sendiri.
- **Path traversal**: URL media dengan `../` ditolak.

## Uji manual yang disarankan sebelum publish

1. `DINEZY_DEBUG=0 python manage.py check --deploy`
2. Pindai header di https://securityheaders.com dan sertifikat SSL di https://www.ssllabs.com/ssltest/
3. Buat user MySQL khusus aplikasi (bukan root) dengan hak hanya atas `db_dinezy`.
4. Batasi port VPS hanya 22, 80, dan 443 dengan firewall (`ufw`). Matikan login SSH memakai password.
5. Jadwalkan backup database harian.
