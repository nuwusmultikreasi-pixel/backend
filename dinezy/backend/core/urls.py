from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import panel, pengumuman_views, perjanjian_views, views

router = DefaultRouter()
router.register(r'tenant', views.TenantViewSet, basename='tenant')
router.register(r'menu', views.MenuViewSet, basename='menu')
router.register(r'order', views.OrderViewSet, basename='order')
router.register(r'meja', views.MejaViewSet, basename='meja')

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('daftar/', views.register_view, name='register'),

    path('login/', views.login_view, name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('api/', include(router.urls)),

    path('panel/', panel.dashboard, name='panel_dashboard'),
    path('panel/cafe/', panel.cafe_list, name='panel_cafe'),
    path('panel/cafe/<int:pk>/kunci/', panel.cafe_kunci, name='panel_cafe_kunci'),
    path('panel/cafe/<int:pk>/akun/', panel.cafe_akun, name='panel_cafe_akun'),
    path('panel/cafe/<int:pk>/tarif/', panel.cafe_tarif, name='panel_cafe_tarif'),
    path('panel/akun/', panel.akun_list, name='panel_akun'),
    path('panel/akun/<int:pk>/password/', panel.akun_password, name='panel_akun_password'),
    path('panel/tagihan/', panel.tagihan_list, name='panel_tagihan'),
    path('panel/perjanjian/', perjanjian_views.panel_perjanjian, name='panel_perjanjian'),
    path('panel/perjanjian/<int:pk>/', perjanjian_views.panel_perjanjian_detail, name='panel_perjanjian_detail'),
    path('panel/perjanjian/<int:pk>/unggah/', perjanjian_views.panel_perjanjian_unggah, name='panel_perjanjian_unggah'),
    path('panel/pengumuman/', pengumuman_views.panel_pengumuman, name='panel_pengumuman'),
    path('panel/pengumuman/baru/', pengumuman_views.panel_pengumuman_form, name='panel_pengumuman_baru'),
    path('panel/pengumuman/<int:pk>/', pengumuman_views.panel_pengumuman_detail, name='panel_pengumuman_detail'),
    path('panel/pengumuman/<int:pk>/ubah/', pengumuman_views.panel_pengumuman_form, name='panel_pengumuman_ubah'),
    path('panel/pengumuman/<int:pk>/hapus/', pengumuman_views.panel_pengumuman_hapus, name='panel_pengumuman_hapus'),
    path('pesan/<int:pk>/lampiran/', pengumuman_views.pesan_lampiran, name='pesan_lampiran'),
    path('perjanjian/<int:pk>/final/', perjanjian_views.unduh_final, name='perjanjian_final'),
    path('syarat-ketentuan/', perjanjian_views.syarat_view, name='syarat'),
    path('panel/tagihan/<int:pk>/bayar/', panel.tagihan_bayar, name='panel_tagihan_bayar'),
    path('invoice/<int:pk>/', panel.invoice_view, name='invoice'),
    path('<slug:tenant_slug>/kasir/', views.kasir_page, name='kasir_dashboard'),
    path('<slug:tenant_slug>/owner/', views.owner_dashboard, name='owner_dashboard'),
    path('<slug:tenant_slug>/owner/setelan/', views.owner_setelan, name='owner_setelan'),
    path('<slug:tenant_slug>/owner/perjanjian/', perjanjian_views.owner_perjanjian, name='owner_perjanjian'),
    path('<slug:tenant_slug>/owner/laporan/', views.owner_laporan, name='owner_laporan'),
    path('<slug:tenant_slug>/owner/pesan/<int:pk>/', pengumuman_views.owner_pesan, name='owner_pesan'),
]
