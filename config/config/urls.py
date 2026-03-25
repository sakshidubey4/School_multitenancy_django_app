"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include  # include only, no django.views import

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('student_management_system.urls')),

    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    
     
]
