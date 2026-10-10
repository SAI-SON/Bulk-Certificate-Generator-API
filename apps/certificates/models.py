import uuid
from django.db import models
from django.conf import settings


def certificate_upload_path(instance, filename):
    return f"{settings.CERTIFICATE_UPLOAD_DIR}/batch_{instance.batch.id}/{filename}"


class Certificate(models.Model):
    STATUS_CHOICES = (
        ("generated", "Generated"),
        ("failed", "Failed"),
        ("revoked", "Revoked"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        "batches.CertificateBatch", on_delete=models.CASCADE, related_name="certificates"
    )
    
    recipient_name = models.CharField(max_length=255)
    recipient_email = models.EmailField(blank=True, null=True)
    course_name = models.CharField(max_length=255, blank=True)
    completion_date = models.DateField(blank=True, null=True)
    
    # Public verification ID
    certificate_id = models.CharField(max_length=100, unique=True, db_index=True)
    
    generated_file = models.FileField(upload_to=certificate_upload_path, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="generated")
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revocation_reason = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.certificate_id} - {self.recipient_name}"
