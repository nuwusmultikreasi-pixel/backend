from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_userprofile'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='menu',
            options={'ordering': ['-tersedia', 'kategori', 'nama_menu']},
        ),
        migrations.AddField(
            model_name='menu',
            name='deskripsi',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='menu',
            name='kategori',
            field=models.CharField(
                choices=[('Makanan', 'Makanan'), ('Minuman', 'Minuman'), ('Snack', 'Snack'),
                         ('Dessert', 'Dessert'), ('Lainnya', 'Lainnya')],
                default='Makanan', max_length=20),
        ),
        migrations.AddField(
            model_name='menu',
            name='tersedia',
            field=models.BooleanField(default=True),
        ),
    ]
