from django.contrib import admin
from .models import CertificateBatch


@admin.register(CertificateBatch)
class CertificateBatchAdmin(admin.ModelAdmin):
    list_display = ("name", "id", "owner", "status", "total_records", "successful_records", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "id", "owner__username")
    readonly_fields = ("id", "created_at", "started_at", "completed_at")
