from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_tenant_print_settings_cleanup"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="pw_enc",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="pw_set_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
