# Dinezy

**Smarter Dining, Made Easy**
QR Ordering & Payment Platform for Restaurants and Cafés

Dikembangkan dan dikelola oleh **PT Nuwus Multikreasi Digital**, Malang.

---

## Cara cepat menjalankan

**Windows:** klik dua kali `jalankan.bat`.

**Linux / server:** `./start.sh`

**Manual:**

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/Mac
pip install -r requirements.txt
copy .env.example .env          # Windows  (Linux: cp .env.example .env)
python manage.py migrate
python manage.py runserver
```

Panduan lengkap ada di [`docs/CARA_MENJALANKAN.md`](docs/CARA_MENJALANKAN.md).

---

## Susunan folder

Kode dipisah menjadi dua bagian besar: **backend** (logika, data, keamanan) dan
**frontend** (tampilan yang dilihat pengguna). Keduanya tetap berada dalam satu
sistem sehingga cukup satu perintah untuk menjalankan semuanya.

```
dinezy/
├── backend/                    ← semua logika program (Python/Django)
│   ├── config/                 ← pengaturan sistem
│   │   ├── settings.py         ← identitas, database, keamanan, tarif, denda
│   │   ├── urls.py             ← daftar alamat halaman
│   │   └── wsgi.py / asgi.py   ← titik masuk saat dipasang di server
│   └── core/                   ← inti aplikasi
│       ├── models.py           ← struktur tabel database
│       ├── views.py            ← pemrosesan halaman cafe (menu, kasir, owner)
│       ├── panel.py            ← halaman panel admin developer
│       ├── perjanjian.py       ← PKS: penomoran, isi, tanda tangan
│       ├── perjanjian_views.py ← alur tanda tangan PKS
│       ├── pengumuman.py       ← template surat & pengumuman
│       ├── billing.py          ← tagihan bulanan dan denda keterlambatan
│       ├── accounts.py         ← pembuatan akun + email kredensial
│       ├── security.py         ← header keamanan, anti brute force, rate limit
│       ├── uploads.py          ← pemeriksaan & pembersihan file gambar
│       ├── serializers.py      ← validasi data API
│       ├── tests.py            ← 31 pengujian otomatis
│       └── migrations/         ← riwayat perubahan struktur database
│
├── frontend/                   ← semua yang dilihat pengguna
│   ├── templates/              ← halaman HTML
│   │   ├── landing.html        ← halaman promosi
│   │   ├── login.html          ← halaman masuk
│   │   ├── register.html       ← pendaftaran cafe
│   │   ├── menu.html           ← menu digital untuk pelanggan (hasil scan QR)
│   │   ├── kasir.html          ← layar kasir
│   │   ├── owner.html          ← dasbor pemilik cafe
│   │   ├── laporan.html        ← laporan penjualan
│   │   ├── panel/              ← halaman panel admin developer
│   │   ├── perjanjian/         ← PKS dan Syarat & Ketentuan
│   │   ├── pengumuman/         ← surat resmi untuk cafe
│   │   ├── emails/             ← isi email
│   │   └── partials/           ← potongan yang dipakai berulang
│   └── static/core/            ← tampilan & aset
│       ├── dinezy.css          ← gaya utama
│       ├── auth.css            ← gaya halaman login & daftar
│       ├── panel.css           ← gaya panel admin
│       ├── dinezy-ui.js        ← perilaku antarmuka
│       ├── print-templates.js  ← desain nota, tiket dapur, QR meja
│       └── img/                ← logo, favicon, maskot, tanda tangan
│
├── media/                      ← file unggahan (logo cafe, QRIS, foto menu)
├── docs/                       ← dokumentasi
├── manage.py                   ← perintah Django
├── requirements.txt            ← daftar paket
├── .env.example                ← contoh pengaturan rahasia
├── jalankan.bat                ← jalankan di Windows
└── start.sh                    ← jalankan di server
```

### Yang perlu diingat saat mengubah kode

| Mau mengubah | Buka folder |
|---|---|
| Tampilan, warna, tulisan di halaman | `frontend/` |
| Logo dan gambar | `frontend/static/core/img/` |
| Perhitungan, data, aturan bisnis | `backend/core/` |
| Tarif, denda, identitas PT, keamanan | `backend/config/settings.py` atau `.env` |
| Isi PKS dan Syarat & Ketentuan | `frontend/templates/perjanjian/` |

Backend tidak menyimpan HTML, dan frontend tidak menyimpan logika program.
Jika menambah file CSS atau gambar baru, letakkan di `frontend/static/core/`
lalu panggil dengan `{% static 'core/nama-file' %}` seperti biasa.

---

## Identitas merek

| | |
|---|---|
| Nama layanan | Dinezy |
| Tagline | Smarter Dining, Made Easy |
| Deskripsi | QR Ordering & Payment Platform for Restaurants and Cafés |
| Badan hukum | PT Nuwus Multikreasi Digital |

Nama, tagline, dan deskripsi diambil dari satu sumber di `backend/config/settings.py`
(`DINEZY_NAMA`, `DINEZY_TAGLINE`, `DINEZY_DESKRIPSI`) dan tersedia di seluruh halaman
sebagai `{{ brand.nama }}`, `{{ brand.tagline }}`, `{{ brand.deskripsi }}`.

**Dokumen hukum tetap atas nama PT Nuwus Multikreasi Digital.** Kop surat PKS,
Syarat & Ketentuan, dan surat pengumuman memakai nama, alamat, nomor SK, serta
logo perusahaan — Dinezy disebut sebagai nama layanan yang diselenggarakan.
Logo perusahaan untuk kop surat: `frontend/static/core/img/nuwus-mark-navy.png`.
Logo layanan untuk aplikasi: `frontend/static/core/img/dinezy-mark-navy.png`.
