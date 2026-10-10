from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CertificateTemplateViewSet

router = DefaultRouter()
router.register(r"templates", CertificateTemplateViewSet, basename="template")

urlpatterns = [
    path("", include(router.urls)),
]
