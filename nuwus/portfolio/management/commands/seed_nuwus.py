"""
Mengisi data awal: akun admin, contoh produk, dan contoh logo mitra.
Pemakaian:  python manage.py seed_nuwus
Ganti/hapus data contoh ini lewat dashboard admin di website.
"""
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw, ImageFont

from portfolio.models import Partner, Product

PRODUCTS = [
    {
        "name": "Contoh Produk — Sistem Informasi Sekolah",
        "category": "Pendidikan",
        "tagline": "Platform akademik terpadu untuk sekolah.",
        "description": (
            "Ini adalah data contoh. Ganti dengan produk Anda lewat menu Admin › Produk.\n\n"
            "Sistem informasi sekolah untuk mengelola data siswa, guru, jadwal, nilai, "
            "dan pengumuman dalam satu dashboard yang mudah digunakan."
        ),
        "url": "https://example.com",
        "tech_stack": "Laravel, MySQL, Bootstrap",
        "year": 2026,
    },
    {
        "name": "Contoh Produk — Toko Online UMKM",
        "category": "E-Commerce",
        "tagline": "Website toko online siap jualan untuk UMKM.",
        "description": (
            "Ini adalah data contoh. Ganti dengan produk Anda lewat menu Admin › Produk.\n\n"
            "Katalog produk, keranjang belanja, checkout via WhatsApp, dan laporan penjualan sederhana."
        ),
        "url": "https://example.com",
        "tech_stack": "Django, PostgreSQL, Tailwind",
        "year": 2026,
    },
    {
        "name": "Contoh Produk — Company Profile",
        "category": "Company Profile",
        "tagline": "Website profil perusahaan yang cepat dan profesional.",
        "description": (
            "Ini adalah data contoh. Ganti dengan produk Anda lewat menu Admin › Produk.\n\n"
            "Website company profile responsif dengan halaman layanan, portofolio, dan formulir kontak."
        ),
        "url": "https://example.com",
        "tech_stack": "Laravel, Blade",
        "year": 2026,
    },
]

PARTNERS = ["Mitra Satu", "Mitra Dua", "Mitra Tiga", "Mitra Empat", "Mitra Lima"]
PALETTE = ["#0a52ef", "#f26608", "#000000"]


def _logo_png(text: str, color: str) -> bytes:
    img = Image.new("RGBA", (360, 120), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
    except OSError:
        font = ImageFont.load_default()
    d.rounded_rectangle((8, 28, 72, 92), radius=14, fill=color)
    d.text((40, 60), text[0], font=font, fill="white", anchor="mm")
    d.text((90, 60), text, font=font, fill=color, anchor="lm")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class Command(BaseCommand):
    help = "Isi data awal (admin, contoh produk, contoh mitra)."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin")
        parser.add_argument("--password", default="nuwus12345")

    def handle(self, *args, **opts):
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=opts["username"],
            defaults={"is_staff": True, "is_superuser": True, "email": ""},
        )
        if created:
            user.set_password(opts["password"])
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Admin dibuat: {opts['username']} / {opts['password']}"))
        else:
            self.stdout.write("Admin sudah ada, dilewati.")

        if not Product.objects.exists():
            for i, data in enumerate(PRODUCTS):
                Product.objects.create(order=i, **data)
            self.stdout.write(self.style.SUCCESS(f"{len(PRODUCTS)} contoh produk ditambahkan."))

        if not Partner.objects.exists():
            for i, name in enumerate(PARTNERS):
                p = Partner(name=name, order=i)
                p.logo.save(f"mitra-{i + 1}.png", ContentFile(_logo_png(name, PALETTE[i % 3])), save=False)
                p.save()
            self.stdout.write(self.style.SUCCESS(f"{len(PARTNERS)} contoh mitra ditambahkan."))
