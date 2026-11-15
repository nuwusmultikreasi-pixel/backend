from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import Partner, Product


class ProductSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()
    tech_list = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "category", "tagline", "description", "url",
            "tech_stack", "tech_list", "thumbnail", "thumbnail_url", "year",
            "order", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["slug", "created_at", "updated_at"]
        extra_kwargs = {"thumbnail": {"write_only": True, "required": False}}

    def get_thumbnail_url(self, obj):
        if not obj.thumbnail:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.thumbnail.url) if request else obj.thumbnail.url

    def get_tech_list(self, obj):
        return [t.strip() for t in (obj.tech_stack or "").split(",") if t.strip()]


class PartnerSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Partner
        fields = ["id", "name", "logo", "logo_url", "website", "order", "is_active", "created_at"]
        read_only_fields = ["created_at"]
        extra_kwargs = {"logo": {"write_only": True}}

    def get_logo_url(self, obj):
        if not obj.logo:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.logo.url) if request else obj.logo.url

    def update(self, instance, validated_data):
        # Logo boleh tidak dikirim ulang saat edit
        if "logo" in validated_data and not validated_data["logo"]:
            validated_data.pop("logo")
        return super().update(instance, validated_data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs["username"], password=attrs["password"])
        if not user or not user.is_active:
            raise serializers.ValidationError("Username atau password salah.")
        if not user.is_staff:
            raise serializers.ValidationError("Akun ini tidak memiliki akses admin.")
        attrs["user"] = user
        return attrs
