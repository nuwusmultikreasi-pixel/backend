# Backend

| Folder | Aplikasi | Domain |
|---|---|---|
| `dinezy/` | Dinezy (Django, termasuk tampilan HTML-nya) | dinezy.id |
| `nuwus/` | API website Nuwus Multikreasi (Django REST) | api-nuwus.dinezy.id |

Masing-masing folder punya `Dockerfile` sendiri dan di-deploy sebagai aplikasi terpisah di Coolify
(Base Directory `/dinezy` dan `/nuwus`).
