from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("products", views.ProductViewSet, basename="product")
router.register("partners", views.PartnerViewSet, basename="partner")

urlpatterns = [
    path("auth/login/", views.login, name="api-login"),
    path("auth/logout/", views.logout, name="api-logout"),
    path("auth/me/", views.me, name="api-me"),
    path("stats/", views.stats, name="api-stats"),
    path("", include(router.urls)),
]
