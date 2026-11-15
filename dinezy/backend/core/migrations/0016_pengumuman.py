import core.models
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_denda_token_pesanan"),
    ]

    operations = [
        migrations.CreateModel(
            name="Pengumuman",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("nomor", models.CharField(blank=True, default="", max_length=60)),
                (
                    "kategori",
                    models.CharField(
                        choices=[
                            ("maintenance", "Pemeliharaan sistem"),
                            ("gangguan", "Gangguan layanan"),
                            ("pembaruan", "Pembaruan aplikasi"),
                            ("pks", "Perjanjian & ketentuan"),
                            ("tagihan", "Tagihan"),
                            ("surat", "Surat resmi"),
                            ("info", "Informasi"),
                        ],
                        default="info",
                        max_length=20,
                    ),
                ),
                ("judul", models.CharField(max_length=150)),
                ("isi", models.TextField()),
                (
                    "penerima",
                    models.CharField(
                        choices=[("semua", "Semua cafe"), ("pilih", "Cafe tertentu")],
                        default="semua",
                        max_length=10,
                    ),
                ),
                ("tampil_banner", models.BooleanField(default=False)),
                ("berlaku_sampai", models.DateTimeField(blank=True, null=True)),
                (
                    "lampiran",
                    models.FileField(
                        blank=True, null=True, upload_to=core.models._pengumuman_path
                    ),
                ),
                (
                    "dibuat_oleh",
                    models.CharField(blank=True, default="", max_length=150),
                ),
                ("dibuat", models.DateTimeField(auto_now_add=True)),
                ("diubah", models.DateTimeField(auto_now=True)),
                (
                    "tenants",
                    models.ManyToManyField(
                        blank=True, related_name="pengumuman_khusus", to="core.tenant"
                    ),
                ),
            ],
            options={
                "ordering": ["-dibuat"],
            },
        ),
        migrations.CreateModel(
            name="PengumumanBaca",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("waktu", models.DateTimeField(auto_now_add=True)),
                (
                    "pengumuman",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dibaca",
                        to="core.pengumuman",
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pengumuman_dibaca",
                        to="core.tenant",
                    ),
                ),
            ],
            options={
                "unique_together": {("pengumuman", "tenant")},
            },
        ),
    ]
