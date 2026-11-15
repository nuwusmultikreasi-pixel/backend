from django.db import models
from django.utils.text import slugify


class Product(models.Model):
    """Produk website/aplikasi yang sudah dibuat oleh PT Nuwus Multikreasi Digital."""

    name = models.CharField("Nama produk", max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    category = models.CharField("Kategori", max_length=80, blank=True)
    tagline = models.CharField("Ringkasan singkat", max_length=200, blank=True)
    description = models.TextField("Deskripsi lengkap")
    url = models.URLField("Link website", max_length=300)
    tech_stack = models.CharField(
        "Teknologi", max_length=200, blank=True, help_text="Pisahkan dengan koma, mis. Laravel, MySQL"
    )
    thumbnail = models.ImageField("Gambar/thumbnail", upload_to="products/", blank=True, null=True)
    year = models.PositiveSmallIntegerField("Tahun", blank=True, null=True)
    order = models.PositiveIntegerField("Urutan", default=0)
    is_active = models.BooleanField("Tampilkan", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
        ordering = ["order", "-created_at"]
        verbose_name = "Produk"
        verbose_name_plural = "Produk"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:160] or "produk"
            slug, i = base, 2
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, i = f"{base}-{i}", i + 1
            self.slug = slug
        super().save(*args, **kwargs)


class Partner(models.Model):
    """Mitra yang sudah bekerja sama — logonya tampil sebagai running text."""

    name = models.CharField("Nama mitra", max_length=150)
    logo = models.ImageField("Logo", upload_to="partners/")
    website = models.URLField("Website mitra", max_length=300, blank=True)
    order = models.PositiveIntegerField("Urutan", default=0)
    is_active = models.BooleanField("Tampilkan", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "partners"
        ordering = ["order", "name"]
        verbose_name = "Mitra"
        verbose_name_plural = "Mitra"

    def __str__(self):
        return self.name
