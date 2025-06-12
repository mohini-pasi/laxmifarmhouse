from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('booking/', views.booking_view, name='booking'),
    path('create-order/', views.create_order, name='create_order'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),

    # Admin panel routes
    path('admin/login/', views.admin_login, name='admin_login'),
    path('admin/logout/', views.admin_logout, name='admin_logout'),
    path('admin/', views.admin_dashboard, name='admin_panel'),
    path('admin/download/', views.download_excel, name='download_excel'),
    path('admin/download/pdf/', views.download_pdf, name='download_pdf'),

    path('admin/clear-all/', views.clear_all_bookings, name='clear_all_bookings'),

    path('booking/', views.booking_view, name='booking'),
]
