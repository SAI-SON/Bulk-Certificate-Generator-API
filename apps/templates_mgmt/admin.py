from django.contrib import admin
from .models import CertificateTemplate


@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at", "updated_at")
    list_filter = ("owner", "created_at")
    search_fields = ("name", "owner__username")
    readonly_fields = ("width", "height", "created_at", "updated_at")
