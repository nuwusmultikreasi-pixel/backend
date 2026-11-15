from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.views import serve as static_serve
from django.urls import include, path, re_path
from django.views.static import serve as media_serve

from core.security import admin_login_redirect
from core.views import menu_page

urlpatterns = [
    path(settings.DINEZY_ADMIN_PATH + 'login/', admin_login_redirect),
    path(settings.DINEZY_ADMIN_PATH, admin.site.urls),
    path('menu/<str:slug>/', menu_page, name='menu_pelanggan'),
    path('', include('core.urls')),
]

if settings.DEBUG or settings.DINEZY_SERVE_FILES:
    urlpatterns = [
        re_path(r'^static/(?P<path>.*)$', static_serve, {'insecure': True}),
        re_path(r'^media/(?!perjanjian/|pengumuman/)(?P<path>.+\.(?i:png|jpe?g|jfif|webp|gif))$', media_serve,
                {'document_root': settings.MEDIA_ROOT}),
    ] + urlpatterns
