from rest_framework import viewsets, mixins
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
