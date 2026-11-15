from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_remove_table_tenant_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='bukti_pembayaran',
            field=models.ImageField(blank=True, null=True, upload_to='payment_proofs/'),
        ),
        migrations.AddField(
            model_name='order',
            name='metode_pembayaran',
            field=models.CharField(choices=[('TUNAI', 'Tunai'), ('QRIS', 'QRIS')], default='TUNAI', max_length=10),
        ),
        migrations.AddField(
            model_name='tenant',
            name='is_locked',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='tenant',
            name='qris_image',
            field=models.ImageField(blank=True, null=True, upload_to='tenant_qris/'),
        ),
        migrations.AddField(
            model_name='tenant',
            name='unpaid_bill',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='order',
            name='status_pesanan',
            field=models.CharField(choices=[('Pending', 'Belum Dibayar'), ('Menunggu', 'Menunggu Konfirmasi Kasir'), ('Diproses', 'Diproses Dapur'), ('Selesai', 'Selesai')], default='Pending', max_length=25),
        ),
    ]
