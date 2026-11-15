from django.db import migrations, models


def hapus_data_basi(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    basi = ContentType.objects.filter(app_label='core', model__in=['table', 'monthlybill'])
    Permission.objects.filter(content_type__in=basi).delete()
    basi.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_invoice_tenant_lock_reason'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.AddField(
            model_name='tenant', name='print_type',
            field=models.CharField(choices=[('58', 'Printer thermal 58 mm'), ('80', 'Printer thermal 80 mm'), ('a5', 'Kertas A5 (printer biasa)'), ('a4', 'Kertas A4 (printer biasa)')], default='80', max_length=3),
        ),
        migrations.AddField(
            model_name='tenant', name='kitchen_print',
            field=models.CharField(choices=[('masuk', 'Otomatis saat pesanan masuk'), ('proses', 'Otomatis saat pesanan diproses kasir'), ('off', 'Manual (tombol "Dapur")')], default='masuk', max_length=10),
        ),
        migrations.AddField(
            model_name='tenant', name='nota_footer',
            field=models.CharField(blank=True, default='Terima kasih atas kunjungan Anda!', max_length=120),
        ),
        migrations.AddField(
            model_name='tenant', name='nota_show_qr',
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(hapus_data_basi, migrations.RunPython.noop),
    ]
