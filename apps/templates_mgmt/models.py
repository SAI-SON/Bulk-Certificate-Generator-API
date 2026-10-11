import os
import uuid
from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.utils.text import get_valid_filename


def template_upload_path(instance, filename):
    filename = get_valid_filename(filename)
    base, ext = os.path.splitext(filename)
    safe_base = base[:50]
    unique_name = f"{safe_base}_{uuid.uuid4().hex[:8]}{ext}"
    return f"{settings.TEMPLATE_UPLOAD_DIR}/user_{instance.owner.id}/{unique_name}"


class CertificateTemplate(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="templates",
        help_text="Administrator who owns this template.",
    )
    name = models.CharField(max_length=255, help_text="User-friendly name for this template.")
    template_file = models.ImageField(
        max_length=500,
        upload_to=template_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=settings.ALLOWED_TEMPLATE_FORMATS)],
        help_text="Background image for the certificate.",
    )
    width = models.PositiveIntegerField(
        help_text="Width of the template image in pixels.", editable=False
    )
    height = models.PositiveIntegerField(
        help_text="Height of the template image in pixels.", editable=False
    )
    field_configuration = models.JSONField(
        default=dict,
        help_text="JSON mapping of certificate fields to their X, Y coordinates, font, and color.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.owner.username})"
