from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CertificateBatchViewSet

router = DefaultRouter()
router.register(r"batches", CertificateBatchViewSet, basename="batch")

urlpatterns = [
    path("", include(router.urls)),
]
