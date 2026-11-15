# Dinezy — Cara Menjalankan & Publish

## A. Menjalankan di komputer (Laragon + MySQL)

1. **Laragon → Start All.** Pastikan MySQL berwarna hijau.
2. Pastikan database **`db_dinezy`** ada (buat di phpMyAdmin/HeidiSQL lalu import `db_dinezy.sql` jika belum).
3. Buka folder `dinezy`, lalu **klik dua kali `jalankan.bat`**. File ini akan:
   - mengaktifkan virtualenv (`..\.venv` atau `venv`),
   - membuat file `.env` dari `.env.example` jika belum ada,
   - **memeriksa koneksi database** (`cek_database`) dan memberi saran jika gagal,
   - menerapkan migrasi, lalu menjalankan server di `http://127.0.0.1:8000`.

Atau secara manual:
```
..\.venv\Scripts\activate
python manage.py cek_database
python manage.py runserver 0.0.0.0:8000
```

> **Virtualenv:** gunakan `.venv` di folder induk (berisi Django 6.1 + semua paket).
> Jika folder `dinezy\venv` lama ikut terhapus saat mengganti folder, tidak masalah,
> `jalankan.bat` otomatis memakai `..\.venv`. Membuat ulang: `python -m venv ..\.venv`
> lalu `pip install -r requirements.txt`.

## B. Jika muncul "database tidak nyambung"

Jalankan `python manage.py cek_database`. Perintah ini menampilkan host/port/nama DB,
mencoba tersambung, lalu memberi **SARAN** sesuai jenis error:

| Error | Arti | Solusi |
|---|---|---|
| `(2003) Can't connect` | MySQL belum menyala / port beda | Start MySQL di Laragon; samakan `DINEZY_DB_PORT` di `.env` |
| `(1049) Unknown database` | DB `db_dinezy` belum ada | Buat DB lalu import `db_dinezy.sql` |
| `(1045) Access denied` | user/password salah | Ubah `DINEZY_DB_USER` / `DINEZY_DB_PASSWORD` di `.env` |
| `no such column / doesn't exist` | migrasi belum jalan | `python manage.py migrate` (otomatis saat server start) |

Saat website berjalan dan database bermasalah, pengguna melihat halaman penjelasan
(bukan error 500), dan API mengembalikan status 503.

## C. Fitur "auto reload" database

- **Sambungan ulang otomatis:** koneksi dicek sebelum dipakai (`CONN_HEALTH_CHECKS`).
  Jika MySQL sempat restart / "server has gone away", Django membuka koneksi baru sendiri.
- **Migrasi otomatis:** setiap server start (runserver maupun wsgi saat publish), migrasi
  yang belum diterapkan langsung dijalankan (`DINEZY_AUTO_MIGRATE=1`).
- **Data di layar diperbarui otomatis:** Kasir tiap 5 detik (pesanan) & 20 detik (menu),
  Owner tiap 30 detik, halaman pelanggan tiap 15 detik (status tersedia/habis).

## D. Catatan data Anda (db_dinezy.sql)

- Kunci lama (`is_locked = 1`) pada NUWUS & Pipir Lepen dibuka otomatis oleh migrasi `0007`,
  karena kini kunci diatur oleh sistem tagihan. Admin tetap bisa mengunci manual dari panel.
- Akun yang sudah terhubung: `Faza` (owner NUWUS), `Samid` (kasir NUWUS),
  `DHIMAS` (owner Pipir Lepen), `Jeje` (kasir Pipir Lepen).
  Saat login pilih cafe yang sesuai (kode: `nuwus` / `Mlipir`).
- Migrasi `0006` (kolom tersedia/deskripsi/kategori menu) akan diterapkan otomatis.

## E. Publish ke hosting

1. Upload folder `dinezy`, buat virtualenv, `pip install -r requirements.txt`
   (Linux: tambah `pip install gunicorn`).
2. Buat database MySQL di hosting, import `db_dinezy.sql`.
3. Salin `.env.example` → `.env`, isi:
   ```
   DINEZY_DEBUG=0
   DINEZY_SECRET_KEY=<teks acak panjang>
   DINEZY_ALLOWED_HOSTS=domainanda.com,www.domainanda.com
   DINEZY_CSRF_TRUSTED_ORIGINS=https://domainanda.com,https://www.domainanda.com
   DINEZY_DB_NAME=... DINEZY_DB_USER=... DINEZY_DB_PASSWORD=... DINEZY_DB_HOST=...
   DINEZY_EMAIL_PASSWORD=<App Password Gmail>
   ```
4. Jalankan:
   - **Linux/VPS:** `./start.sh` (migrate + collectstatic + gunicorn).
   - **cPanel "Setup Python App" / PythonAnywhere:** arahkan WSGI ke `config/wsgi.py`.
     Migrasi berjalan otomatis saat aplikasi dimuat.
5. File static (CSS/logo) dan media (foto menu) dilayani Django (`DINEZY_SERVE_FILES=1`).
   Jika hosting sudah melayani `/static/` dan `/media/`, set `DINEZY_SERVE_FILES=0`.
   Untuk trafik besar disarankan memakai WhiteNoise/Nginx.

## F. Panel Admin & Tagihan

**Login admin:** buka `/login/`, pilih tab **Admin**, masuk dengan akun superuser/staff
(mis. `Faza`). Tidak perlu lagi mengetik `/admin/`. Panel ada di `/panel/`:
- **Ringkasan**: total cafe, nota bulan ini, tagihan belum dibayar, grafik 6 bulan.
- **Cafe & Akun**: kunci/buka manual, buat/reset akun Owner & Kasir.
- **Tagihan**: semua invoice, filter status, tombol **Tandai lunas**, cetak invoice A4.
- **Biaya layanan per cafe**: di menu *Cafe & Akun* terlihat penjualan bulan ini, bulan lalu, dan rata-rata nota tiap cafe.
  Tombol **Ubah tarif** mengatur biaya layanan khusus cafe itu (standar Rp1.500). Tarif baru berlaku untuk pesanan berikutnya; nota lama tetap memakai biaya yang tercatat.
- **Akun & Password**: lihat username & password Owner/Kasir tiap cafe (tersimpan terenkripsi), salin, atau atur password baru.
  Akun lama yang dibuat sebelum versi ini tampil "Belum tersimpan" sampai akun itu login sekali lagi atau password-nya diatur ulang.
  Admin bawaan Django tetap bisa dibuka manual di `/admin/` bila perlu.

**Aturan tagihan (otomatis, tanpa cron):**
- Rp 1.500 per nota (pesanan yang sudah diproses kasir), diatur `DINEZY_TARIF_PER_NOTA`.
- Biaya ini otomatis ditambahkan ke total belanja pelanggan sebagai **Biaya layanan** (tampil di keranjang, kasir, nota, dan laporan).
  Invoice yang sudah terbit sebelumnya tetap memakai tarif lamanya.
- Invoice bulan lalu terbit otomatis tanggal 1, jatuh tempo akhir bulan berikutnya (1 bulan).
- Lewat jatuh tempo & belum lunas → login Owner & Kasir **diblokir**; halaman login menampilkan
  rincian tagihan + tombol WhatsApp admin. Yang sedang login juga otomatis dikeluarkan.
- Admin klik **Tandai lunas** → akun langsung aktif kembali.
- Penagihan dimulai dari `DINEZY_BILLING_START` (default `2026-11`) agar tidak menagih mundur.
  Untuk demo sidang, set misalnya `DINEZY_BILLING_START=2026-09` di `.env` agar invoice September muncul.
- Isi rekening & WA admin di `.env`: `DINEZY_PAYMENT_BANK`, `DINEZY_PAYMENT_ACCOUNT`, `DINEZY_PAYMENT_NAME`, `DINEZY_ADMIN_WA`.

**Owner** melihat tagihan & mencetak invoice di menu **Tagihan** pada dashboard-nya.

## G. Pendaftaran, Setelan cetak & Laporan

- **Pendaftaran** (`/daftar/`): pendaftar mengisi data cafe, **wajib unggah logo** (PNG/JPG/WEBP ≤ 2 MB),
  serta membuat sendiri **username & password Owner dan Kasir** (password min. 8 karakter, divalidasi).
  Email hanya berisi ringkasan username (password tidak dikirim lewat email).
- **Logo cafe** tampil di nota, kartu QR meja, laporan rekap, dan invoice tagihan.
  Owner dapat menggantinya di menu **Setelan**.
- **Setelan** (dashboard Owner):
  - Jenis printer: thermal **58 mm / 80 mm**, atau kertas **A5 / A4** → layout nota & tiket dapur menyesuaikan.
  - Cetak tiket dapur: otomatis saat pesanan masuk / saat diproses kasir / manual.
  - Pesan di bawah nota & QR "pesan lagi".
- **Tiket dapur** dicetak dari halaman Kasir (tanpa harga, nomor meja besar). Agar langsung tercetak
  tanpa jendela dialog, buka Chrome kasir dengan opsi `--kiosk-printing` dan set printer dapur sebagai default.
  Status otomatis bisa dimatikan per perangkat lewat chip "Cetak dapur" di kanan atas halaman Kasir.
- **Laporan rekap** (Owner → Dashboard → tombol *Laporan Rekap*): A4 siap cetak/PDF berisi ringkasan,
  grafik harian, menu terlaris, metode pembayaran, kategori, jam tersibuk, rincian menu & harian, tanda tangan.

## H. Foto MASKOT di halaman depan
Foto `MASKOT.png` Anda sudah terpasang (sudah dirapikan & diperkecil agar halaman cepat dibuka). Untuk menggantinya:
1. Simpan foto dengan nama persis `MASKOT.png` di folder:
   `dinezy/frontend/static/core/img/MASKOT.png`
   (huruf besar/kecil berpengaruh di hosting Linux; `.jpg`/`.webp` juga dikenali).
2. Paling bagus: PNG **latar transparan** (orang saja, tanpa background), potret, minimal 900×1100 px, ukuran < 800 KB.
   - PNG transparan → tampil "melayang" di depan lingkaran biru.
   - Foto biasa (ada latar) → otomatis dipotong dalam bingkai melengkung.
3. Matikan lalu jalankan ulang `jalankan.bat`, refresh browser (Ctrl+F5).
4. Di hosting, `start.sh` menjalankan `collectstatic` sehingga foto ikut tersalin.
Jika file tidak ada, halaman depan memakai ilustrasi bawaan.

## I. Bersih-bersih
- Folder **`dz-frontend`** (Laravel) **tidak dipakai** sama sekali oleh website ini → aman dihapus.
- Folder **`dinezy\venv`** lama (Django 5.0, tanpa xhtml2pdf) tidak dipakai jika Anda memakai `..\.venv`.
- Migrasi `0008` menghapus sisa data model lama (`core.table`, `core.monthlybill`) dari tabel
  `django_content_type` & `auth_permission`. Tabel `auth_group*`, `auth_user_*_permissions`,
  `django_admin_log`, dan `django_session` **tetap dibutuhkan** Django, jangan dihapus.
- `jalankan.bat` kini juga menjalankan `clearsessions` (hapus sesi login kedaluwarsa).

## J. Perintah berguna

```
python manage.py cek_database              # diagnosa koneksi, migrasi, cafe & akun
python manage.py buat_akun_cafe --cek      # status akun Owner/Kasir tiap cafe
python manage.py buat_akun_cafe nuwus      # buat akun yang belum ada
python manage.py buat_akun_cafe nuwus --reset --kirim-email   # reset password + kirim email
python manage.py changepassword Faza       # ganti password user tertentu
```


## K. Syarat & Ketentuan dan Perjanjian Kerja Sama (PKS)
1. **Saat mendaftar**, cafe wajib mencentang persetujuan Syarat & Ketentuan (`/syarat-ketentuan/`). Waktu, IP, dan versi S&K tercatat otomatis.
2. **PKS dibuat otomatis** untuk setiap cafe (termasuk cafe lama) dengan nomor `001/PKS/DNZ-NM/<bulan romawi>/<tahun>`.
3. **Owner menandatangani** dari dashboard: banner *Tanda tangani Perjanjian Kerja Sama* atau menu *Profil & Akun → Perjanjian Kerja Sama*. Tanda tangan digambar di layar; sistem menyimpan waktu, IP, perangkat, dan kode verifikasi dokumen (SHA-256).
4. **Admin** membuka menu *Perjanjian* di panel → *Buka PKS* → *Cetak / PDF* → bubuhkan e-meterai lewat distributor resmi → unggah PDF final. Owner lalu bisa mengunduh PDF bermeterai.
5. **Data PIHAK PERTAMA** diisi di `.env`: `DINEZY_PERUSAHAAN_NAMA`, `DINEZY_PERUSAHAAN_ALAMAT`, `DINEZY_PERUSAHAAN_WAKIL`, `DINEZY_PERUSAHAAN_JABATAN`, `DINEZY_PERUSAHAAN_EMAIL`, `DINEZY_PERUSAHAAN_WA`, `DINEZY_PENGADILAN`, `DINEZY_PKS_BATAS_HARI` (contoh di `.env.example`). Selama belum diisi, dokumen menampilkan teks dalam kurung siku, misalnya `[nama Direktur]`.
6. **Tanda tangan PIHAK PERTAMA (opsional)**: simpan gambar PNG latar transparan di `frontend/static/core/img/ttd-pihak-pertama.png`.
7. **Keamanan file**: tanda tangan dan PDF final disimpan di `media/perjanjian/` dan tidak bisa dibuka lewat URL publik. Jika memakai Nginx untuk `/media/`, tambahkan `location /media/perjanjian/ { deny all; }`.
8. **Mengubah isi S&K/PKS**: edit `frontend/templates/perjanjian/syarat.html` dan `frontend/templates/perjanjian/_isi_pks.html`, lalu naikkan `VERSI` dan `BERLAKU_SEJAK` di `backend/core/perjanjian.py`. Mintalah notaris/konsultan hukum memeriksa isi sebelum dipakai.
9. **Perubahan biaya layanan**: sesuai Pasal 5 PKS, umumkan ke semua cafe paling lambat 30 hari sebelum tarif baru diubah di panel admin.

## L. Versi 23: QRIS, alur PKS, denda, dan keamanan

**Pendaftaran.** Formulir kini punya kolom unggah QRIS (opsional, bisa menyusul di menu Setelan owner). Setelah formulir dikirim, owner otomatis masuk dan langsung diarahkan ke halaman tanda tangan PKS. Setelah menandatangani, owner dibawa ke dashboard.

**QRIS pelanggan.** Saat pelanggan memilih QRIS, halaman menu menampilkan gambar QRIS cafe beserta total bayar dan tombol "Simpan gambar QRIS".

**PKS versi 1.1.**
- Pasal 6 mengatur masa tenggang 3 hari setelah jatuh tempo. Setelah itu dikenakan denda 1‰ per hari, maksimal 10% dari nilai invoice.
- Pasal 10 mengatur masa berlangganan minimum 3 bulan.
- Identitas PIHAK PERTAMA memakai PT NUWUS MULTIKREASI DIGITAL beserta nomor SK AHU. Isi `DINEZY_PERUSAHAAN_NIB` di `.env` bila NIB sudah terbit.

Besaran denda diatur di `.env`:

```
DINEZY_DENDA_TENGGANG_HARI=3
DINEZY_DENDA_PERMIL_HARI=1
DINEZY_DENDA_MAKS_PERSEN=10
```

Denda tampil di invoice, di tab Tagihan owner, di panel admin, dan di notifikasi blokir saat login. Ketika admin menandai invoice lunas, nilai denda saat itu dikunci.

**Keamanan.**
- Login dikunci 15 menit setelah 5 kali gagal (`DINEZY_LOGIN_MAKS_GAGAL`, `DINEZY_LOGIN_KUNCI_MENIT`).
- Setiap gambar yang diunggah (logo, QRIS, foto menu, bukti bayar) diperiksa isinya, ditulis ulang, dan diberi nama acak.
- Pesanan pelanggan hanya bisa dibuka atau diberi bukti bayar dengan token rahasia milik pesanan itu.
- Header CSP, nosniff, Referrer-Policy, dan Permissions-Policy terpasang.
- Halaman login dan dashboard tidak disimpan di cache browser.
- API dibatasi jumlah permintaannya (throttling).
- MySQL berjalan dalam mode STRICT.
- Bila `DINEZY_SECRET_KEY` kosong, kunci acak dibuat otomatis di file `.secret_key`. Jangan bagikan file ini.

**Saat publish (VPS):**

```
DINEZY_DEBUG=0
DINEZY_SECRET_KEY=<teks acak minimal 50 karakter>
DINEZY_ALLOWED_HOSTS=domainanda.id,www.domainanda.id
DINEZY_CSRF_TRUSTED_ORIGINS=https://domainanda.id,https://www.domainanda.id
DINEZY_HTTPS=1
DINEZY_TRUST_PROXY=1
DINEZY_ADMIN_PATH=kelola-rahasia/
```

Untuk database, buat user MySQL khusus (bukan root) yang hanya punya hak atas `db_dinezy`.

**Uji otomatis:** `python manage.py test core`

## M. Versi 24: pengumuman, berkas, dan keamanan lanjutan

- **Panel Admin > Pengumuman & Surat**: tulis pengumuman atau surat untuk semua cafe atau cafe tertentu. Tersedia 8 templat: pemeliharaan, gangguan, layanan pulih, pembaruan aplikasi, pembaruan PKS, penyesuaian biaya, pengingat tagihan, dan surat resmi. Kategori Perjanjian, Tagihan, dan Surat resmi tampil sebagai surat berkop dengan tanda tangan direktur. Pesan juga bisa dilampiri PDF dan ditampilkan sebagai banner di dasbor owner dan kasir.
- **Dasbor owner > Berkas & Pesan**: berisi PKS, PKS final bermeterai, S&K, dan kotak pesan dari admin. Pesan yang belum dibaca diberi tanda merah.
- **Tanda tangan direktur** otomatis tampil di setiap PKS dan surat resmi. Untuk mengganti tanda tangan, timpa file `frontend/static/core/img/ttd-pihak-pertama.png` dengan PNG berlatar transparan. Admin tinggal membubuhkan e-meterai lalu mengunggah PDF final di menu Perjanjian.
- **Keamanan**: lihat `UJI_KEAMANAN.md`.
