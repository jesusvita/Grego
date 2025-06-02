"""
URL configuration for chat_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf.urls import include # Keep this if you use it elsewhere, or just 'include' from django.urls
from chat import views as chat_views # Import your chat app's views
from django.urls import include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Decide what your root URL should be. Example: list_active_rooms
    # path('', chat_views.list_active_rooms, name='home_page'), 
    # Or if you have a separate home.html:
    path('', chat_views.home_view, name='home_page'), # Assuming home_view serves a general landing page
    path('create_room/', chat_views.create_room_view, name='create_room'),  # New URL for creating/entering a room
    path('rooms/', chat_views.list_active_rooms, name='list_active_rooms'), # New route for listing rooms
    path('chat/', include('chat.urls')),
    path('accounts/', include('accounts.urls')),
]
