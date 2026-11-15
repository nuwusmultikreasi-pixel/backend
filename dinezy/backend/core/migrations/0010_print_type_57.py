from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_userprofile_pw_enc"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tenant",
            name="print_type",
            field=models.CharField(
                choices=[
                    ("57", "Printer thermal 57 x 30 mm"),
                    ("58", "Printer thermal 58 mm"),
                    ("80", "Printer thermal 80 mm"),
                    ("a5", "Kertas A5 (printer biasa)"),
                    ("a4", "Kertas A4 (printer biasa)"),
                ],
                default="80",
                max_length=3,
            ),
        ),
    ]
