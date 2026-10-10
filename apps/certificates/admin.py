from django.contrib import admin
from .models import Certificate


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("certificate_id", "recipient_name", "batch", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("certificate_id", "recipient_name", "recipient_email", "batch__id")
    readonly_fields = ("id", "certificate_id", "created_at", "revoked_at")
