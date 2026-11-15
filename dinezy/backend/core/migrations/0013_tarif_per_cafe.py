from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_catatan_item"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="tarif_diubah",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="tenant",
            name="tarif_layanan",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Biaya layanan per nota khusus cafe ini (Rp). Kosong = tarif standar.",
                null=True,
            ),
        ),
    ]
