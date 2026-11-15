from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Partner, Product
from .permissions import IsStaffOrReadOnly
from .serializers import LoginSerializer, PartnerSerializer, ProductSerializer


class _AdminAwareViewSet(viewsets.ModelViewSet):
    """Publik hanya melihat data aktif; admin (staff) melihat semua data."""

    permission_classes = [IsStaffOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = self.queryset.all()
        user = self.request.user
        if not (user and user.is_authenticated and user.is_staff):
            qs = qs.filter(is_active=True)
        return qs


class ProductViewSet(_AdminAwareViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class PartnerViewSet(_AdminAwareViewSet):
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data["user"]
    token, _ = Token.objects.get_or_create(user=user)
    return Response({
        "token": token.key,
        "user": {"id": user.id, "username": user.username, "name": user.get_full_name() or user.username},
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    Token.objects.filter(user=request.user).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    u = request.user
    return Response({"id": u.id, "username": u.username, "name": u.get_full_name() or u.username})


@api_view(["GET"])
@permission_classes([AllowAny])
def stats(request):
    return Response({
        "products": Product.objects.filter(is_active=True).count(),
        "partners": Partner.objects.filter(is_active=True).count(),
    })
