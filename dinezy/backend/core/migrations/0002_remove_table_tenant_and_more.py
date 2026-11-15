import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='table',
            name='tenant',
        ),
        migrations.RenameField(
            model_name='order',
            old_name='nama_pelanggan',
            new_name='nama_pemesan',
        ),
        migrations.RemoveField(
            model_name='menu',
            name='deskripsi',
        ),
        migrations.RemoveField(
            model_name='menu',
            name='is_available',
        ),
        migrations.RemoveField(
            model_name='order',
            name='biaya_layanan',
        ),
        migrations.RemoveField(
            model_name='order',
            name='bukti_bayar',
        ),
        migrations.RemoveField(
            model_name='order',
            name='email_pelanggan',
        ),
        migrations.RemoveField(
            model_name='order',
            name='metode_pembayaran',
        ),
        migrations.RemoveField(
            model_name='order',
            name='status',
        ),
        migrations.RemoveField(
            model_name='order',
            name='subtotal',
        ),
        migrations.RemoveField(
            model_name='order',
            name='total_bayar',
        ),
        migrations.RemoveField(
            model_name='orderitem',
            name='subtotal',
        ),
        migrations.AddField(
            model_name='menu',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='status_pesanan',
            field=models.CharField(choices=[('Pending', 'Pending'), ('Diproses', 'Diproses'), ('Selesai', 'Selesai')], default='Pending', max_length=20),
        ),
        migrations.AddField(
            model_name='order',
            name='total_harga',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='menu',
            name='harga',
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name='menu',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='order',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='order',
            name='nomor_meja',
            field=models.CharField(max_length=20),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='harga_satuan',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='menu',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.menu'),
        ),
        migrations.AlterField(
            model_name='tenant',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='tenant',
            name='slug',
            field=models.SlugField(unique=True),
        ),
        migrations.AlterField(
            model_name='tenant',
            name='status',
            field=models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active', max_length=20),
        ),
        migrations.DeleteModel(
            name='MonthlyBill',
        ),
        migrations.DeleteModel(
            name='Table',
        ),
    ]
