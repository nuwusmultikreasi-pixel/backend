import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Menu',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nama_menu', models.CharField(max_length=100)),
                ('harga', models.DecimalField(decimal_places=0, max_digits=10)),
                ('deskripsi', models.TextField(blank=True, null=True)),
                ('foto', models.ImageField(blank=True, null=True, upload_to='menu_photos/')),
                ('is_available', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nomor_meja', models.CharField(max_length=10)),
                ('nama_pelanggan', models.CharField(max_length=100)),
                ('email_pelanggan', models.EmailField(max_length=254)),
                ('subtotal', models.DecimalField(decimal_places=0, max_digits=12)),
                ('biaya_layanan', models.DecimalField(decimal_places=0, default=1000, max_digits=10)),
                ('total_bayar', models.DecimalField(decimal_places=0, max_digits=12)),
                ('metode_pembayaran', models.CharField(choices=[('qris', 'QRIS'), ('cash', 'Tunai / Kasir')], max_length=10)),
                ('bukti_bayar', models.ImageField(blank=True, null=True, upload_to='bukti_bayar/')),
                ('status', models.CharField(choices=[('menunggu_verifikasi', 'Menunggu Verifikasi'), ('lunas', 'Lunas'), ('ditolak', 'Ditolak')], default='menunggu_verifikasi', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Tenant',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nama_cafe', models.CharField(max_length=100)),
                ('slug', models.SlugField(max_length=100, unique=True)),
                ('nama_owner', models.CharField(max_length=100)),
                ('email_owner', models.EmailField(max_length=254)),
                ('whatsapp', models.CharField(max_length=20)),
                ('alamat', models.TextField()),
                ('logo', models.ImageField(blank=True, null=True, upload_to='tenant_logos/')),
                ('status', models.CharField(choices=[('pending', 'Pending Verifikasi'), ('active', 'Aktif'), ('locked', 'Terkunci (Auto-Lock)')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('jumlah', models.IntegerField(default=1)),
                ('harga_satuan', models.DecimalField(decimal_places=0, max_digits=10)),
                ('subtotal', models.DecimalField(decimal_places=0, max_digits=10)),
                ('menu', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='core.menu')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='core.order')),
            ],
        ),
        migrations.CreateModel(
            name='Table',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nomor_meja', models.CharField(max_length=10)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tables', to='core.tenant')),
            ],
        ),
        migrations.AddField(
            model_name='order',
            name='tenant',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='orders', to='core.tenant'),
        ),
        migrations.CreateModel(
            name='MonthlyBill',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bulan_tahun', models.CharField(max_length=7)),
                ('total_invoice', models.IntegerField(default=0)),
                ('total_tagihan', models.DecimalField(decimal_places=0, max_digits=12)),
                ('status', models.CharField(choices=[('unpaid', 'Belum Dibayar'), ('paid', 'Lunas'), ('overdue', 'Tunggakan')], default='unpaid', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bills', to='core.tenant')),
            ],
        ),
        migrations.AddField(
            model_name='menu',
            name='tenant',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='menus', to='core.tenant'),
        ),
    ]
