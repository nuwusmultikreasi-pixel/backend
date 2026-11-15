from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .accounts import ensure_cafe_accounts, send_credentials_email
from django.shortcuts import redirect

from .models import Tenant, Menu, Order, OrderItem, Meja, UserProfile, Invoice

admin.site.register(OrderItem)
admin.site.register(Meja)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'tenant', 'role')
    list_filter = ('role', 'tenant')
    search_fields = ('user__username', 'tenant__nama_cafe')

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name = 'Cafe & Peran'
    verbose_name_plural = 'Cafe & Peran'
    fk_name = 'user'


admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = ('username', 'email', 'get_cafe', 'get_role', 'is_active', 'is_superuser')

    @admin.display(description='Cafe')
    def get_cafe(self, obj):
        p = getattr(obj, 'profile', None)
        return p.tenant if p and p.tenant else '-'

    @admin.display(description='Peran')
    def get_role(self, obj):
        p = getattr(obj, 'profile', None)
        return p.get_role_display() if p else '-'


def _buat_akun(modeladmin, request, queryset, reset):
    for t in queryset:
        akun = ensure_cafe_accounts(t, reset_password=reset)
        if not akun:
            messages.info(request, f"{t.nama_cafe}: akun Owner & Kasir sudah ada.")
            continue
        terkirim = send_credentials_email(t, akun, request.build_absolute_uri('/'))
        detail = ' | '.join(f"{a['role']}: {a['username']} / {a['password']}" for a in akun)
        status = f"dikirim ke {t.email_owner}" if terkirim else "EMAIL GAGAL, catat kredensial ini"
        messages.success(request, f"{t.nama_cafe} (kode: {t.slug}) — {detail} — {status}")


@admin.action(description='Buat akun Owner & Kasir yang belum ada (+ kirim email)')
def buat_akun_cafe(modeladmin, request, queryset):
    _buat_akun(modeladmin, request, queryset, reset=False)


@admin.action(description='Reset password Owner & Kasir (+ kirim email)')
def reset_akun_cafe(modeladmin, request, queryset):
    _buat_akun(modeladmin, request, queryset, reset=True)


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    actions = [buat_akun_cafe, reset_akun_cafe]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            _buat_akun(self, request, [obj], reset=False)
    
    list_display = ('nama_cafe', 'nama_owner', 'whatsapp', 'status', 'unpaid_bill', 'is_locked', 'lock_reason')
    list_filter = ('status', 'is_locked')
    search_fields = ('nama_cafe', 'nama_owner', 'email_owner')
    prepopulated_fields = {'slug': ('nama_cafe',)}
    
    fieldsets = (
        ('Informasi Dasar', {
            'fields': ('nama_cafe', 'slug', 'nama_owner', 'email_owner', 'whatsapp', 'alamat', 'logo', 'status')
        }),
        ('Pembayaran & Tagihan (Admin)', {
            'fields': ('qris_image', 'unpaid_bill', 'is_locked', 'lock_reason'),
            'classes': ('collapse',),
        }),
    )

@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ('nama_menu', 'tenant', 'kategori', 'harga', 'tersedia')
    list_filter = ('tenant', 'kategori', 'tersedia')
    list_editable = ('tersedia',)
    search_fields = ('nama_menu',)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('harga_satuan',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('nama_pemesan', 'tenant', 'nomor_meja', 'metode_pembayaran', 'status_pesanan', 'total_harga', 'created_at')
    list_filter = ('status_pesanan', 'metode_pembayaran', 'tenant', 'created_at')
    search_fields = ('nama_pemesan', 'nomor_meja')
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Informasi Pesanan', {
            'fields': ('tenant', 'nama_pemesan', 'nomor_meja', 'total_harga', 'status_pesanan')
        }),
        ('Informasi Pembayaran', {
            'fields': ('metode_pembayaran', 'bukti_pembayaran'),
        }),
    )


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'tenant', 'tahun', 'bulan', 'jumlah_nota', 'total', 'status', 'jatuh_tempo')
    list_filter = ('status', 'tenant', 'tahun')
    search_fields = ('tenant__nama_cafe',)


def _login_redirect(request, extra_context=None):
    nxt = request.GET.get('next', '/panel/')
    return redirect(f'/login/?mode=admin&next={nxt}')


admin.site.login = _login_redirect
admin.site.site_header = 'Dinezy'
admin.site.site_title = 'Dinezy'
admin.site.index_title = 'Data Lanjutan'
