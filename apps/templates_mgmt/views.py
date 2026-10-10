from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from apps.accounts.permissions import IsOwner
from .models import CertificateTemplate
from .serializers import CertificateTemplateSerializer


class CertificateTemplateViewSet(viewsets.ModelViewSet):
    """
    API endpoints for managing certificate templates.
    Only the owner of a template can view, update, or delete it.
    """
    serializer_class = CertificateTemplateSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_queryset(self):
        # Filter templates so a user only sees their own
        return CertificateTemplate.objects.filter(owner=self.request.user)
