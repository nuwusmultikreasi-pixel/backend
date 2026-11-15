from django.contrib import admin

from .models import Partner, Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "url", "year", "order", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("name", "category", "description")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("name", "website", "order", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("name",)
