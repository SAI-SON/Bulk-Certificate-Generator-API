from rest_framework import serializers
from .models import Certificate


class CertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        fields = (
            "id",
            "batch",
            "recipient_name",
            "recipient_email",
            "course_name",
            "completion_date",
            "certificate_id",
            "generated_file",
            "status",
            "error_message",
            "created_at",
            "revoked_at",
            "revocation_reason",
        )
        read_only_fields = fields
