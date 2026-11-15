from django.db import migrations, models
import django.db.models.deletion


def reset_kunci_lama(apps, schema_editor):
    Tenant = apps.get_model('core', 'Tenant')
    Tenant.objects.all().update(is_locked=False, lock_reason='', unpaid_bill=0)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_menu_tersedia_deskripsi_kategori'),
    ]

    operations = [
        migrations.AddField(
            model_name='tenant',
            name='lock_reason',
            field=models.CharField(blank=True, choices=[('', '-'), ('tagihan', 'Tagihan belum dibayar'), ('manual', 'Dikunci manual oleh admin')], default='', max_length=10),
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tahun', models.PositiveIntegerField()),
                ('bulan', models.PositiveSmallIntegerField()),
                ('jumlah_nota', models.PositiveIntegerField(default=0)),
                ('tarif', models.PositiveIntegerField(default=1000)),
                ('total', models.PositiveIntegerField(default=0)),
                ('status', models.CharField(choices=[('unpaid', 'Belum Dibayar'), ('paid', 'Lunas')], default='unpaid', max_length=10)),
                ('tanggal_terbit', models.DateField()),
                ('jatuh_tempo', models.DateField()),
                ('dibayar_pada', models.DateTimeField(blank=True, null=True)),
                ('catatan', models.CharField(blank=True, default='', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invoices', to='core.tenant')),
            ],
            options={
                'ordering': ['-tahun', '-bulan', 'tenant__nama_cafe'],
                'unique_together': {('tenant', 'tahun', 'bulan')},
            },
        ),
        migrations.RunPython(reset_kunci_lama, migrations.RunPython.noop),
    ]
