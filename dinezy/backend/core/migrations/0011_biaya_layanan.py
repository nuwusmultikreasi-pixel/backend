from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_print_type_57"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="biaya_layanan",
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="invoice",
            name="tarif",
            field=models.PositiveIntegerField(default=1500),
        ),
    ]
