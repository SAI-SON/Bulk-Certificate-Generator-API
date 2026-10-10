import uuid
from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator


def participant_upload_path(instance, filename):
    return f"{settings.PARTICIPANT_UPLOAD_DIR}/user_{instance.owner.id}/{instance.id}_{filename}"


class CertificateBatch(models.Model):
    STATUS_CHOICES = (
        ("uploaded", "Uploaded"),
        ("validated", "Validated"),
        ("queued", "Queued"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("partially_completed", "Partially Completed"),
        ("failed", "Failed"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="batches"
    )
    name = models.CharField(max_length=255)
    template = models.ForeignKey(
        "templates_mgmt.CertificateTemplate", on_delete=models.RESTRICT, related_name="batches"
    )
    participant_file = models.FileField(
        upload_to=participant_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=["csv", "xlsx"])],
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="uploaded")
    
    total_records = models.PositiveIntegerField(default=0)
    processed_records = models.PositiveIntegerField(default=0)
    successful_records = models.PositiveIntegerField(default=0)
    failed_records = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    error_summary = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Certificate Batches"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["owner", "status"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
