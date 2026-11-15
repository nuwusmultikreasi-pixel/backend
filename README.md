# Backend

| Folder | Aplikasi | Domain |
|---|---|---|
| `dinezy/` | Dinezy (Django) | dinezy.id |
| `nuwus/` | API website Nuwus Multikreasi (Django REST) | api-nuwus.dinezy.id |

Masing-masing folder punya `Dockerfile` sendiri dan di-deploy sebagai aplikasi terpisah di Coolify
(Base Directory `/dinezy` dan `/nuwus`).

Tampilan Dinezy (templates & static) ada di repo `frontend`, folder `dinezy/`.
Saat build, `dinezy/docker/ambil_tampilan.py` mengambil folder itu ke `dinezy/frontend/`.
Untuk menjalankan Dinezy di komputer sendiri, salin folder `dinezy/` dari repo frontend ke `dinezy/frontend/`.
