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

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', chat_views.index, name='index'),  # Route for the root URL
    path('chat/', include('chat.urls')),
]
