from django.urls import path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from . import views

schema_view = get_schema_view(
    openapi.Info(
        title="Members API",
        default_version='v1',
        description="API for member management",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('', views.login_view, name='login'),
    path('home/', views.home, name='home'),
    path('logout/', views.logout_view, name='logout'),
    
    path('member/<int:id>/delete/', views.delete_member, name='delete_member'),
    path('export-members/', views.export_members_csv, name='export_members'),
    path('import-members/', views.import_members_csv, name='import_members'),
    path("manage-teacher-permissions/", views.manage_teacher_permissions, name="manage_teacher_permissions"),
    path("create-school-admin/", views.create_school_and_admin, name="create_school_admin"),
    
    path("super-admin/", views.super_admin_dashboard, name="super_admin_dashboard"),
    path("super-admin/school/<int:school_id>/edit/", views.edit_school, name="edit_school"),
    path("super-admin/school/<int:school_id>/delete/", views.delete_school, name="delete_school"),
    


    # Swagger / OpenAPI
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('accounts/logout/', views.logout_view, name='accounts_logout'),
]
