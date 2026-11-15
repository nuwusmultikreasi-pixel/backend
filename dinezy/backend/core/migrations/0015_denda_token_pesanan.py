import secrets

from django.db import migrations, models

import core.models


def isi_token(apps, schema_editor):
    Order = apps.get_model('core', 'Order')
    for pk in Order.objects.values_list('pk', flat=True).iterator():
        Order.objects.filter(pk=pk).update(akses_token=secrets.token_urlsafe(32))


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_perjanjian'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='denda',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='order',
            name='akses_token',
            field=models.CharField(default=core.models.token_pesanan, editable=False, max_length=43),
        ),
        migrations.RunPython(isi_token, migrations.RunPython.noop),
    ]
