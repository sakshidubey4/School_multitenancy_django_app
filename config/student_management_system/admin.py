from django.contrib import admin
from .models import School, Member


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code")
    search_fields = ("name", "code")


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "role", "school")
    list_filter = ("role", "school")
    search_fields = ("name", "email")
