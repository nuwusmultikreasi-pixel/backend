from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_biaya_layanan"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="catatan",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
    ]
