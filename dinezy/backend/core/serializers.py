from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from .billing import tarif
from .models import Meja, Menu, Order, OrderItem, Tenant
from .uploads import bersihkan_gambar


def gambar_aman(value, label, **opsi):
    if not value:
        return value
    try:
        return bersihkan_gambar(value, label, **opsi)
    except DjangoValidationError as e:
        raise serializers.ValidationError(e.messages) from e


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'nama_cafe', 'slug', 'logo', 'qris_image', 'status']

class MenuSerializer(serializers.ModelSerializer):
    class Meta:
        model = Menu
        fields = ['id', 'nama_menu', 'deskripsi', 'kategori', 'harga', 'foto', 'tersedia', 'tenant']
        read_only_fields = ['tenant']

    def validate_foto(self, value):
        return gambar_aman(value, 'Foto menu', maks_mb=5, maks_sisi=1200)

    def validate_nama_menu(self, value):
        value = ' '.join(value.split())
        if not value:
            raise serializers.ValidationError('Nama menu wajib diisi.')
        return value

    def validate_harga(self, value):
        if value is None or value < 0:
            raise serializers.ValidationError('Harga tidak boleh negatif.')
        return value

class OrderItemSerializer(serializers.ModelSerializer):
    nama_menu = serializers.ReadOnlyField(source='menu.nama_menu')

    class Meta:
        model = OrderItem
        fields = ['id', 'menu', 'nama_menu', 'jumlah', 'harga_satuan', 'catatan']
        read_only_fields = ['harga_satuan']
        extra_kwargs = {'catatan': {'required': False, 'allow_blank': True}}

    def validate_catatan(self, value):
        value = ' '.join(str(value or '').split())
        if len(value) > 150:
            raise serializers.ValidationError('Catatan maksimal 150 karakter.')
        return value

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, required=False)
    subtotal = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = [
            'id', 'tenant', 'nama_pemesan', 'nomor_meja', 'total_harga', 'biaya_layanan', 'subtotal',
            'metode_pembayaran', 'bukti_pembayaran', 'status_pesanan',
            'created_at', 'items', 'akses_token',
        ]
        read_only_fields = ['total_harga', 'biaya_layanan', 'bukti_pembayaran', 'akses_token']

    def validate_nama_pemesan(self, value):
        value = ' '.join(value.split())
        if not value:
            raise serializers.ValidationError('Nama pemesan wajib diisi.')
        return value

    def validate_nomor_meja(self, value):
        return ' '.join(value.split())

    def validate(self, attrs):
        items = attrs.get('items') or []
        if self.instance is not None:
            if 'tenant' in attrs and attrs['tenant'].pk != self.instance.tenant_id:
                raise serializers.ValidationError({'tenant': 'Cafe pesanan tidak dapat diubah.'})
            return attrs
        if not items:
            raise serializers.ValidationError({'items': 'Pesanan minimal berisi 1 menu.'})
        if len(items) > 50:
            raise serializers.ValidationError({'items': 'Maksimal 50 jenis menu dalam satu pesanan.'})
        tenant = attrs.get('tenant')
        if tenant is None or tenant.status != 'active':
            raise serializers.ValidationError({'tenant': 'Cafe tidak tersedia.'})
        for item in items:
            menu = item['menu']
            if tenant and menu.tenant_id != tenant.id:
                raise serializers.ValidationError({'items': f'Menu "{menu.nama_menu}" bukan milik cafe ini.'})
            if not menu.tersedia:
                raise serializers.ValidationError({'items': f'Maaf, menu "{menu.nama_menu}" sedang habis.'})
            if not 1 <= item.get('jumlah', 0) <= 99:
                raise serializers.ValidationError({'items': 'Jumlah tiap item 1 sampai 99.'})
        return attrs

    def update(self, instance, validated_data):
        validated_data.pop('items', None)
        validated_data.pop('tenant', None)
        return super().update(instance, validated_data)

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        validated_data['status_pesanan'] = 'Pending'
        order = Order.objects.create(**validated_data)
        subtotal = 0
        baris = []
        for item in items_data:
            menu = item['menu']
            baris.append(OrderItem(order=order, menu=menu, jumlah=item['jumlah'], harga_satuan=menu.harga,
                                   catatan=item.get('catatan', '') or ''))
            subtotal += menu.harga * item['jumlah']
        OrderItem.objects.bulk_create(baris)
        order.biaya_layanan = tarif(order.tenant)
        order.total_harga = subtotal + order.biaya_layanan
        order.save(update_fields=['biaya_layanan', 'total_harga'])
        return order


class UploadBuktiSerializer(serializers.ModelSerializer):
    bukti_pembayaran = serializers.ImageField(required=True)

    class Meta:
        model = Order
        fields = ['bukti_pembayaran']

    def validate_bukti_pembayaran(self, value):
        return gambar_aman(value, 'Bukti pembayaran', maks_mb=5, maks_sisi=1600)

class MejaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meja
        fields = ['id', 'tenant', 'nomor_meja', 'created_at']
        read_only_fields = ['tenant', 'created_at']
        validators = []

    def validate_nomor_meja(self, value):
        value = ' '.join(value.split())
        if not value:
            raise serializers.ValidationError('Nomor meja wajib diisi.')
        return value