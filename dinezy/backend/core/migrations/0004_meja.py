import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_order_bukti_pembayaran_order_metode_pembayaran_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Meja',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nomor_meja', models.CharField(max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='meja_list', to='core.tenant')),
            ],
            options={
                'ordering': ['nomor_meja'],
                'unique_together': {('tenant', 'nomor_meja')},
            },
        ),
    ]
