from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.views import serve as static_serve
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve as media_serve

admin.site.site_header = "Nuwus Multikreasi Digital — Admin"
admin.site.site_title = "Nuwus Admin"


def index(request):
    """Halaman root backend: hanya penunjuk arah (tampilan website ada di Laravel)."""
    return JsonResponse({
        "service": "Nuwus API (Django)",
        "endpoints": ["/api/products/", "/api/partners/"],
        "website": "http://127.0.0.1:8000",
    })


urlpatterns = [
    path("", index),
    path("admin/", admin.site.urls),
    path("api/", include("portfolio.urls")),
]

# Sajikan file upload (logo mitra & thumbnail produk)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif settings.SERVE_FILES:
    urlpatterns += [
        re_path(r"^static/(?P<path>.*)$", static_serve, {"insecure": True}),
        re_path(r"^media/(?P<path>.*)$", media_serve, {"document_root": settings.MEDIA_ROOT}),
    ]
