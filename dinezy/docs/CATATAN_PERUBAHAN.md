# Dinezy — Pembaruan

## Yang baru
- **Halaman profil/penawaran** di `/` (sebelum login): fitur, peran, cara kerja,
  plus form **Pendaftaran Cafe** dan **Login** berdampingan.
- **Pendaftaran otomatis**: menyimpan Cafe (Tenant) + akun **Owner** & **Kasir** ke database,
  lalu mengirim username & password ke email pendaftar.
  Jika SMTP belum diatur, kredensial ditampilkan SEKALI di halaman sukses.
- **Login per cafe**: isi Nama/Kode Cafe + username + password. Akun cafe lain ditolak.
- **Owner**: tab baru *Kelola Menu* (tambah/ubah/hapus, foto, kategori, deskripsi, status) + tab *Akun*.
- **Kasir**: tab baru *Daftar Menu* dengan saklar Tersedia / Habis.
- **Pelanggan**: menu habis tampil monokrom, label HABIS, tidak bisa ditambahkan.
  Status disinkron tiap 15 detik; server juga menolak pesanan berisi menu habis.
- Desain baru (putih + biru gelap/navy, layout sidebar untuk Owner & Kasir) di semua halaman: `core/static/core/dinezy.css`.

## Perbaikan bug lama
- URL API tidak lagi terkunci ke `127.0.0.1` (sekarang bisa diakses dari HP lewat IP lokal).
- Nomor meja seperti `VIP-1` tidak lagi berubah jadi `0`.
- Nama menu di kartu pesanan kasir dulu tampil "Item"; sekarang tampil benar.
- Grafik metode pembayaran owner dulu memasukkan "TUNAI" ke "Lainnya".
- Keamanan API: pengunjung tanpa login tidak bisa lagi menghapus cafe, mengubah menu,
  atau melihat daftar seluruh pesanan.

## Pembaruan terbaru
- Logo Dinezy dipasang di semua halaman, favicon, dan email (`core/static/core/img/`).
- Login kini di halaman sendiri (`/login/`), Pendaftaran di halaman sendiri (`/daftar/`).
- Pilihan cafe di halaman login diambil langsung dari database.
- Login lebih toleran: username tidak peka huruf besar/kecil, spasi di password ditoleransi,
  dan kode cafe boleh dikosongkan (sistem memakai cafe milik akun tersebut).

## Tampilan Owner & Kasir (terbaru)
- Navigasi berbentuk kapsul di kiri: hanya ikon, melebar otomatis saat kursor diarahkan.
  Di HP berubah menjadi kapsul di bawah layar.
- Latar biru tua dengan ilustrasi siluet suasana cafe yang bergerak pelan
  (`core/static/core/img/cafe-silhouette.svg`). Animasi mati otomatis jika
  perangkat diatur "kurangi gerakan".
- Nota 80 mm baru & kartu QR meja (cetak satuan / "Cetak Semua QR" 4 kartu per A4
  dengan garis potong): `core/static/core/print-templates.js`.

## Kenapa akun lama tidak bisa login?
Cafe yang dibuat SEBELUM fitur pendaftaran (lewat admin) belum punya akun Owner/Kasir,
atau akun user-nya belum dihubungkan ke cafe. Perbaiki dengan salah satu cara:

1. Cek status akun semua cafe:
       python manage.py buat_akun_cafe --cek
2. Buat akun yang belum ada (password ditampilkan di terminal):
       python manage.py buat_akun_cafe                 (semua cafe)
       python manage.py buat_akun_cafe CAFE --kirim-email
   Ganti password akun yang sudah ada:  tambahkan --reset
3. Atau lewat Admin: Tenants -> centang cafe -> Action
   "Buat akun Owner & Kasir yang belum ada" / "Reset password Owner & Kasir".
4. Menghubungkan user lama secara manual: Admin -> Users -> pilih user ->
   bagian "Cafe & Peran" -> pilih cafe dan peran (Owner/Kasir).
Cafe baru yang dibuat lewat Admin kini otomatis dibuatkan akun.

## Cara menjalankan
1. Aktifkan venv seperti biasa, lalu:
       python manage.py migrate        (menambah kolom tersedia/deskripsi/kategori pada Menu)
       python manage.py runserver 0.0.0.0:8000
2. Buka http://127.0.0.1:8000/
   (Tanpa MySQL? set env `DINEZY_USE_SQLITE=1` untuk memakai db.sqlite3.)

## Agar email benar-benar terkirim (Gmail)
1. Aktifkan Verifikasi 2 Langkah di akun Gmail pengirim.
2. Buat App Password (Akun Google -> Keamanan -> Sandi Aplikasi).
3. Isi `EMAIL_HOST_PASSWORD` di `config/settings.py` (atau env `DINEZY_EMAIL_PASSWORD`).
