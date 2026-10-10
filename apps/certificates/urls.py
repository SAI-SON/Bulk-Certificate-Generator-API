from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CertificateViewSet, CertificateVerificationView

router = DefaultRouter()
router.register(r"certificates", CertificateViewSet, basename="certificate")

urlpatterns = [
    path("", include(router.urls)),
    path("verify/<str:certificate_id>/", CertificateVerificationView.as_view(), name="verify"),
]
