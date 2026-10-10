from rest_framework import serializers
from .models import CertificateTemplate
from .validators import validate_field_configuration


class CertificateTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CertificateTemplate
        fields = (
            "id",
            "name",
            "template_file",
            "width",
            "height",
            "field_configuration",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "width", "height", "created_at", "updated_at")

    def validate_field_configuration(self, value):
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            validate_field_configuration(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))
        return value

    def create(self, validated_data):
        # We need to set the width and height of the template before saving it.
        # Pillow is used to read the image dimensions.
        from PIL import Image
        
        image_file = validated_data.get("template_file")
        if image_file:
            try:
                with Image.open(image_file) as img:
                    validated_data["width"] = img.width
                    validated_data["height"] = img.height
            except Exception as e:
                raise serializers.ValidationError({"template_file": f"Invalid image file: {str(e)}"})
                
        # Set the owner to the user making the request
        validated_data["owner"] = self.context["request"].user
        
        return super().create(validated_data)
