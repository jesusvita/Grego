from django.urls import path

from . import views

app_name = 'chat' # Optional: add app namespace
urlpatterns = [
    path('', views.home_view, name='home'),
    path('<str:room_name>/', views.room, name='room'),
    path('qr/review/', views.review_qr_view, name='review_qr'),
    path('qr/menu/', views.menu_qr_view, name='menu_qr'),
]