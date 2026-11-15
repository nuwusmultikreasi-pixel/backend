"""
Menyiapkan database PT NUWUS MULTIKREASI DIGITAL secara otomatis:
  1. membuat database MySQL (bila belum ada),
  2. membuat semua tabel (migrate),
  3. mengisi akun admin + data contoh (hanya bila masih kosong).

Aman dijalankan berulang kali: data yang sudah ada tidak dihapus.
Pemakaian:  python setup_database.py
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)
sys.path.insert(0, str(BASE_DIR))

try:
    from dotenv import load_dotenv
    import pymysql
except ImportError:
    print("[X] Paket Python belum terpasang. Jalankan: python -m pip install -r requirements.txt")
    sys.exit(1)

load_dotenv(BASE_DIR / ".env")

cfg = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DB_PORT", "3306")),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
}
db_name = os.environ.get("DB_NAME", "nuwus_db")

print(f"[1/3] Menghubungi MySQL di {cfg['host']}:{cfg['port']} (user: {cfg['user']}) ...")
try:
    conn = pymysql.connect(**cfg, charset="utf8mb4", connect_timeout=5)
except pymysql.err.OperationalError as e:
    code = e.args[0] if e.args else None
    print()
    if code == 1045:
        print("[X] Username/password MySQL ditolak.")
        print("    Isi DB_USER dan DB_PASSWORD yang benar di file backend\\.env")
    else:
        print("[X] MySQL belum menyala / tidak bisa dihubungi.")
        print("    Buka XAMPP lalu klik Start pada MySQL (atau Laragon -> Start All), lalu jalankan lagi.")
    print(f"    Detail: {e}")
    sys.exit(1)

with conn.cursor() as cur:
    cur.execute(
        f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
conn.close()
print(f"      Database `{db_name}` siap.")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nuwus_api.settings")
import django  # noqa: E402

django.setup()
from django.core.management import call_command  # noqa: E402

print("[2/3] Membuat / memperbarui tabel ...")
call_command("migrate", interactive=False, verbosity=0)
print("      Tabel siap.")

print("[3/3] Mengisi data awal (bila masih kosong) ...")
call_command("seed_nuwus")
print("\nDatabase selesai disiapkan.")
