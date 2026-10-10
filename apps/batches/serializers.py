from rest_framework import serializers
from .models import CertificateBatch
from .validators import validate_participant_file
from apps.templates_mgmt.serializers import CertificateTemplateSerializer


class CertificateBatchSerializer(serializers.ModelSerializer):
    participant_file = serializers.FileField(validators=[validate_participant_file])

    class Meta:
        model = CertificateBatch
        fields = (
            "id",
            "name",
            "template",
            "participant_file",
            "status",
            "total_records",
            "processed_records",
            "successful_records",
            "failed_records",
            "created_at",
            "started_at",
            "completed_at",
            "error_summary",
        )
        read_only_fields = (
            "id",
            "status",
            "total_records",
            "processed_records",
            "successful_records",
            "failed_records",
            "created_at",
            "started_at",
            "completed_at",
            "error_summary",
        )

    def create(self, validated_data):
        validated_data["owner"] = self.context["request"].user
        
        # Ensure the selected template belongs to the user
        template = validated_data["template"]
        if template.owner != validated_data["owner"]:
            raise serializers.ValidationError({"template": "You do not have permission to use this template."})
            
        return super().create(validated_data)


class CertificateBatchDetailSerializer(CertificateBatchSerializer):
    """Serializer for detailed view that includes the full template object."""
    template = CertificateTemplateSerializer(read_only=True)
