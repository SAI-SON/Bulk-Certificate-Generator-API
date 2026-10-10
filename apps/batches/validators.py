import os
from django.conf import settings
from rest_framework import serializers

def validate_participant_file(value):
    """
    Validate that the uploaded file meets the size and extension constraints.
    """
    if value.size > settings.MAX_PARTICIPANT_FILE_SIZE:
        max_mb = settings.MAX_PARTICIPANT_FILE_SIZE / (1024 * 1024)
        raise serializers.ValidationError(f"File size exceeds the {max_mb}MB limit.")
        
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in [".csv", ".xlsx"]:
        raise serializers.ValidationError("Only .csv and .xlsx files are supported.")
        
    return value
