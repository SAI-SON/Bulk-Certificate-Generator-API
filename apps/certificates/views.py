import os
from django.http import FileResponse
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions import IsOwner
from .models import Certificate
from .serializers import CertificateSerializer
from apps.core.pagination import LargePagination


class CertificateViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Read-only API endpoints for viewing generated certificates.
    Users can only view certificates from their own batches.
    """
    serializer_class = CertificateSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = LargePagination
    
    def get_queryset(self):
        return Certificate.objects.filter(batch__owner=self.request.user)

    def get_permissions(self):
        # We enforce that the request user owns the parent batch
        # Note: Since the queryset is filtered, IsOwner isn't strictly necessary for object retrieval,
        # but it adds a layer of semantic correctness.
        return super().get_permissions()

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        certificate = self.get_object()
        
        if certificate.status != "generated" or not certificate.generated_file:
            return Response(
                {"detail": "PDF file is not available for this certificate."},
                status=status.HTTP_404_NOT_FOUND
            )
            
        return FileResponse(
            certificate.generated_file.open('rb'),
            as_attachment=True,
            filename=os.path.basename(certificate.generated_file.name)
        )

