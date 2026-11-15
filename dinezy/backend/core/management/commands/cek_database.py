from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    help = "Memeriksa koneksi database, status migrasi, cafe, dan akun login."
    requires_system_checks = []

    def handle(self, *args, **opts):
        ok, warn, err = self.style.SUCCESS, self.style.WARNING, self.style.ERROR
        db = settings.DATABASES['default']
        self.stdout.write(self.style.MIGRATE_HEADING("== Pengaturan database =="))
        self.stdout.write(f"  Engine : {db['ENGINE']}")
        self.stdout.write(f"  Nama   : {db['NAME']}")
        if 'mysql' in db['ENGINE']:
            self.stdout.write(f"  Host   : {db.get('HOST')}:{db.get('PORT')}   User: {db.get('USER')}   Password: {'(ada)' if db.get('PASSWORD') else '(kosong)'}")

        self.stdout.write(self.style.MIGRATE_HEADING("\n== Koneksi =="))
        try:
            connection.ensure_connection()
            with connection.cursor() as c:
                c.execute('SELECT VERSION()' if 'mysql' in db['ENGINE'] else 'select sqlite_version()')
                self.stdout.write(ok(f"  TERSAMBUNG. Versi server: {c.fetchone()[0]}"))
        except Exception as e:
            self.stdout.write(err(f"  GAGAL: {e}"))
            pesan = str(e).lower()
            if '2003' in pesan or 'refused' in pesan or '10061' in pesan:
                saran = ("MySQL belum menyala atau port salah. Di Laragon klik 'Start All' (MySQL hijau). "
                         f"Cek port di Laragon > Menu > MySQL > my.ini (port=...) lalu samakan DINEZY_DB_PORT di .env (sekarang {db.get('PORT')}).")
            elif '1049' in pesan or 'unknown database' in pesan:
                saran = f"Database '{db['NAME']}' belum ada. Buat di phpMyAdmin/HeidiSQL lalu import db_dinezy.sql."
            elif '1045' in pesan or 'access denied' in pesan:
                saran = "User/password MySQL salah. Sesuaikan DINEZY_DB_USER & DINEZY_DB_PASSWORD di .env."
            elif 'cryptography' in pesan:
                saran = "Install paket: pip install cryptography"
            else:
                saran = "Periksa pengaturan database di file .env."
            self.stdout.write(warn("  SARAN: " + saran))
            raise SystemExit(1) from e

        self.stdout.write(self.style.MIGRATE_HEADING("\n== Migrasi =="))
        ex = MigrationExecutor(connection)
        rencana = ex.migration_plan(ex.loader.graph.leaf_nodes())
        if rencana:
            for m, _ in rencana:
                self.stdout.write(warn(f"  BELUM: {m.app_label}.{m.name}"))
            self.stdout.write("  -> jalankan: python manage.py migrate  (atau biarkan auto-migrate saat runserver)")
        else:
            self.stdout.write(ok("  Semua migrasi sudah diterapkan."))

        from core.models import Tenant
        self.stdout.write(self.style.MIGRATE_HEADING("\n== Cafe & akun login =="))
        try:
            for t in Tenant.objects.all().order_by('id'):
                status = ok('aktif') if t.status == 'active' else err(t.status)
                kunci = warn(f' [DIBLOKIR: {t.get_lock_reason_display()}]') if t.is_locked else ''
                self.stdout.write(f"  - {t.nama_cafe}  (kode: {t.slug}) {status}{kunci}")
                for u, role, aktif in t.users.values_list('user__username', 'role', 'user__is_active'):
                    self.stdout.write(f"       {role:<5} : {u}{'' if aktif else err('  (nonaktif)')}")
                if not t.users.exists():
                    self.stdout.write(warn("       belum ada akun -> python manage.py buat_akun_cafe " + t.slug))
            tanpa = User.objects.filter(profile__isnull=True)
            for u in tanpa:
                ket = 'superuser -> /admin/' if u.is_superuser else warn('belum terhubung ke cafe (tidak bisa login dashboard)')
                self.stdout.write(f"  * user {u.username}: {ket}")
        except Exception as e:
            self.stdout.write(err(f"  Tidak bisa membaca tabel: {e}. Jalankan migrate dahulu."))
