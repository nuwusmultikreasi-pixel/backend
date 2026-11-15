import core.models
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_tarif_per_cafe"),
    ]

    operations = [
        migrations.CreateModel(
            name="Perjanjian",
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
                ("nomor", models.CharField(blank=True, max_length=60)),
                ("versi", models.CharField(default="", max_length=20)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("menunggu", "Menunggu tanda tangan"),
                            ("ditandatangani", "Sudah ditandatangani"),
                            ("bermeterai", "Final bermeterai"),
                        ],
                        default="menunggu",
                        max_length=20,
                    ),
                ),
                ("sk_disetujui_at", models.DateTimeField(blank=True, null=True)),
                ("sk_ip", models.CharField(blank=True, max_length=45)),
                ("nama_penandatangan", models.CharField(blank=True, max_length=120)),
                (
                    "jabatan_penandatangan",
                    models.CharField(blank=True, default="Pemilik", max_length=60),
                ),
                ("tarif_saat_ttd", models.PositiveIntegerField(blank=True, null=True)),
                ("ttd", models.FileField(blank=True, upload_to=core.models._pks_path)),
                ("ttd_at", models.DateTimeField(blank=True, null=True)),
                ("ttd_ip", models.CharField(blank=True, max_length=45)),
                ("ttd_perangkat", models.CharField(blank=True, max_length=255)),
                ("kode_dokumen", models.CharField(blank=True, max_length=64)),
                (
                    "file_final",
                    models.FileField(blank=True, upload_to=core.models._pks_path),
                ),
                ("final_at", models.DateTimeField(blank=True, null=True)),
                ("final_oleh", models.CharField(blank=True, max_length=150)),
                ("dibuat", models.DateTimeField(auto_now_add=True)),
                (
                    "tenant",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="perjanjian",
                        to="core.tenant",
                    ),
                ),
            ],
            options={
                "verbose_name": "Perjanjian Kerja Sama",
                "verbose_name_plural": "Perjanjian Kerja Sama",
            },
        ),
    ]
