import os
from django.http import FileResponse
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.utils import timezone
from apps.accounts.permissions import IsOwner
from .models import Certificate
from .serializers import CertificateSerializer
from apps.core.pagination import LargePagination
from apps.core.throttling import VerificationRateThrottle


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

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        certificate = self.get_object()
        
        reason = request.data.get("reason", "")
        if not reason:
            return Response({"detail": "Revocation reason is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        certificate.status = "revoked"
        certificate.revoked_at = timezone.now()
        certificate.revocation_reason = reason
        certificate.save(update_fields=["status", "revoked_at", "revocation_reason"])
        
        return Response({"detail": "Certificate revoked successfully."})


class CertificateVerificationView(APIView):
    """
    Public endpoint for verifying a certificate.
    """
    permission_classes = [AllowAny]
    throttle_classes = [VerificationRateThrottle]

    def get(self, request, certificate_id):
        try:
            cert = Certificate.objects.get(certificate_id=certificate_id)
            
            if cert.status == "revoked":
                return Response({
                    "valid": False,
                    "message": "This certificate has been revoked.",
                    "revoked_at": cert.revoked_at,
                    "reason": cert.revocation_reason
                }, status=status.HTTP_200_OK)
                
            if cert.status != "generated":
                return Response({
                    "valid": False,
                    "message": "This certificate is not active."
                }, status=status.HTTP_200_OK)

            # Publicly safe data
            return Response({
                "valid": True,
                "certificate_id": cert.certificate_id,
                "recipient_name": cert.recipient_name,
                "course_name": cert.course_name,
                "completion_date": cert.completion_date,
                "issuer": cert.batch.owner.get_full_name() or cert.batch.owner.username
            })
            
        except Certificate.DoesNotExist:
            return Response(
                {"valid": False, "message": "Certificate not found."},
                status=status.HTTP_404_NOT_FOUND
            )


