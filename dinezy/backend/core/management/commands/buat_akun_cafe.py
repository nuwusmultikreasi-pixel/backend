from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from core.accounts import ensure_cafe_accounts, send_credentials_email
from core.models import Tenant


class Command(BaseCommand):
    help = ("Membuat akun Owner & Kasir untuk cafe yang belum punya akun, "
            "lalu menampilkan dan mengirim kredensialnya ke email owner.")

    def add_arguments(self, parser):
        parser.add_argument('cafe', nargs='?', help='Slug / nama cafe. Kosongkan untuk semua cafe.')
        parser.add_argument('--reset', action='store_true', help='Reset password akun yang sudah ada.')
        parser.add_argument('--kirim-email', action='store_true', help='Kirim kredensial ke email owner.')
        parser.add_argument('--base-url', default='http://127.0.0.1:8000', help='Alamat web untuk link login di email.')
        parser.add_argument('--cek', action='store_true', help='Hanya tampilkan status akun tiap cafe.')

    def handle(self, *args, **opts):
        qs = Tenant.objects.all().order_by('id')
        if opts['cafe']:
            qs = qs.filter(slug__iexact=opts['cafe']) | qs.filter(nama_cafe__iexact=opts['cafe'])
            if not qs.exists():
                self.stderr.write(self.style.ERROR(f"Cafe '{opts['cafe']}' tidak ditemukan."))
                return

        if opts['cek']:
            for t in qs:
                akun = list(t.users.values_list('user__username', 'role'))
                status = self.style.SUCCESS('OK') if len(akun) >= 2 else self.style.WARNING('BELUM LENGKAP')
                self.stdout.write(f"[{status}] {t.nama_cafe}  (kode: {t.slug})  akun: {akun or '-'}")
            tanpa = User.objects.filter(profile__isnull=True, is_superuser=False)
            if tanpa.exists():
                self.stdout.write(self.style.WARNING(
                    "User tanpa cafe (tidak bisa login ke dashboard): " + ', '.join(tanpa.values_list('username', flat=True))))
            return

        for t in qs:
            akun = ensure_cafe_accounts(t, reset_password=opts['reset'])
            if not akun:
                self.stdout.write(f"- {t.nama_cafe} ({t.slug}): akun sudah lengkap. Pakai --reset untuk ganti password.")
                continue
            self.stdout.write(self.style.SUCCESS(f"\n{t.nama_cafe}  (kode cafe: {t.slug})"))
            for a in akun:
                self.stdout.write(f"   {a['role']:<6} username: {a['username']:<28} password: {a['password']}")
            if opts['kirim_email']:
                ok = send_credentials_email(t, akun, opts['base_url'])
                self.stdout.write(f"   email ke {t.email_owner}: {'TERKIRIM' if ok else 'GAGAL (cek pengaturan SMTP)'}")
