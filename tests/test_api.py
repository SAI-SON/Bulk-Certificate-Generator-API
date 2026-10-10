import pytest
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile


@pytest.mark.django_db
def test_authentication(api_client, user):
    """Test login to get token"""
    response = api_client.post("/api/v1/auth/login/", {
        "username": user.username,
        "password": "TestPass123!"
    })
    assert response.status_code == status.HTTP_200_OK
    assert "token" in response.data


@pytest.mark.django_db
def test_create_template(auth_client, sample_image, temp_media):
    """Test uploading a template image with JSON configuration"""
    img_file = sample_image()
    
    response = auth_client.post(
        "/api/v1/templates/",
        {
            "name": "Test Template",
            "template_file": img_file,
            "field_configuration": '{"name": {"x": 100, "y": 200, "font_size": 20}}'
        },
        format="multipart"
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["name"] == "Test Template"
    assert response.data["width"] == 800  # From sample_image fixture


@pytest.mark.django_db
def test_create_and_validate_batch(auth_client, user, sample_image, sample_csv, temp_media):
    """Test the full flow up to validation"""
    
    # 1. Create template
    from apps.templates_mgmt.models import CertificateTemplate
    img_file = SimpleUploadedFile("template.png", sample_image().read(), content_type="image/png")
    template = CertificateTemplate.objects.create(
        owner=user,
        name="Test",
        template_file=img_file,
        field_configuration={"name": {"x": 100, "y": 200}},
        width=800,
        height=600
    )
    
    # 2. Create batch
    csv_file = SimpleUploadedFile("part.csv", sample_csv().read(), content_type="text/csv")
    
    response = auth_client.post(
        "/api/v1/batches/",
        {
            "name": "Test Batch",
            "template": template.id,
            "participant_file": csv_file
        },
        format="multipart"
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    batch_id = response.data["id"]
    
    # 3. Validate batch
    val_resp = auth_client.post(f"/api/v1/batches/{batch_id}/validate/")
    assert val_resp.status_code == status.HTTP_200_OK
    assert val_resp.data["status"] == "validated"
    assert val_resp.data["valid_rows"] == 3


@pytest.mark.django_db
def test_batch_generate_sync(auth_client, user, sample_image, sample_csv, temp_media):
    """Test generating a small batch synchronously"""
    
    # 1. Setup
    from apps.templates_mgmt.models import CertificateTemplate
    img_file = SimpleUploadedFile("template.png", sample_image().read(), content_type="image/png")
    template = CertificateTemplate.objects.create(
        owner=user,
        name="Test",
        template_file=img_file,
        field_configuration={"name": {"x": 100, "y": 200}},
        width=800,
        height=600
    )
    
    csv_file = SimpleUploadedFile("part.csv", sample_csv().read(), content_type="text/csv")
    resp_batch = auth_client.post("/api/v1/batches/", {"name": "Test Batch", "template": template.id, "participant_file": csv_file}, format="multipart")
    batch_id = resp_batch.data["id"]
    
    auth_client.post(f"/api/v1/batches/{batch_id}/validate/")
    
    # 2. Generate
    resp_gen = auth_client.post(f"/api/v1/batches/{batch_id}/generate/")
    assert resp_gen.status_code == status.HTTP_200_OK
    
    # 3. Check status
    resp_status = auth_client.get(f"/api/v1/batches/{batch_id}/status/")
    assert resp_status.data["status"] == "completed"
    assert resp_status.data["successful"] == 3
    
    # 4. Check certificates list
    resp_certs = auth_client.get(f"/api/v1/batches/{batch_id}/certificates/")
    assert len(resp_certs.data["results"]) == 3


@pytest.mark.django_db
def test_cross_user_isolation(auth_client, another_auth_client, user, sample_image, temp_media):
    """Test that a user cannot see or modify another user's templates or batches"""
    from apps.templates_mgmt.models import CertificateTemplate
    img_file = SimpleUploadedFile("template.png", sample_image().read(), content_type="image/png")
    template = CertificateTemplate.objects.create(
        owner=user,
        name="Test Template",
        template_file=img_file,
        field_configuration={},
        width=800,
        height=600
    )
    
    # another user tries to fetch the template
    resp = another_auth_client.get(f"/api/v1/templates/{template.id}/")
    assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_certificate_revocation_and_verification(api_client, auth_client, user, sample_image, sample_csv, temp_media):
    """Test revoking a certificate and verifying its public status"""
    from apps.templates_mgmt.models import CertificateTemplate
    
    img_file = SimpleUploadedFile("template.png", sample_image().read(), content_type="image/png")
    template = CertificateTemplate.objects.create(
        owner=user, name="Test", template_file=img_file,
        field_configuration={"name": {"x": 100, "y": 200}}, width=800, height=600
    )
    
    csv_file = SimpleUploadedFile("part.csv", sample_csv().read(), content_type="text/csv")
    resp_batch = auth_client.post("/api/v1/batches/", {"name": "Test Batch", "template": template.id, "participant_file": csv_file}, format="multipart")
    batch_id = resp_batch.data["id"]
    
    auth_client.post(f"/api/v1/batches/{batch_id}/validate/")
    auth_client.post(f"/api/v1/batches/{batch_id}/generate/")
    
    # Get a generated certificate
    certs_resp = auth_client.get(f"/api/v1/batches/{batch_id}/certificates/")
    cert_id_db = certs_resp.data["results"][0]["id"]
    public_cert_id = certs_resp.data["results"][0]["certificate_id"]
    
    # Public Verify (Active)
    verify_resp = api_client.get(f"/api/v1/verify/{public_cert_id}/")
    assert verify_resp.status_code == status.HTTP_200_OK
    assert verify_resp.data["valid"] is True
    
    # Revoke
    revoke_resp = auth_client.post(f"/api/v1/certificates/{cert_id_db}/revoke/", {"reason": "Test revocation"})
    assert revoke_resp.status_code == status.HTTP_200_OK
    
    # Public Verify (Revoked)
    verify_revoked_resp = api_client.get(f"/api/v1/verify/{public_cert_id}/")
    assert verify_revoked_resp.status_code == status.HTTP_200_OK
    assert verify_revoked_resp.data["valid"] is False
    assert "revoked" in verify_revoked_resp.data["message"].lower()
    assert verify_revoked_resp.data["reason"] == "Test revocation"


from unittest.mock import patch

@pytest.mark.django_db
@patch("tasks.generation.generate_certificates_task.delay")
def test_batch_generate_async(mock_delay, auth_client, user, sample_image, sample_csv, temp_media, settings):
    """Test that large batches are queued for celery"""
    settings.SYNC_GENERATION_THRESHOLD = 1  # Force async since sample_csv has 3 rows
    
    from apps.templates_mgmt.models import CertificateTemplate
    img_file = SimpleUploadedFile("template.png", sample_image().read(), content_type="image/png")
    template = CertificateTemplate.objects.create(
        owner=user, name="Test", template_file=img_file,
        field_configuration={"name": {"x": 100, "y": 200}}, width=800, height=600
    )
    
    csv_file = SimpleUploadedFile("part.csv", sample_csv().read(), content_type="text/csv")
    resp_batch = auth_client.post("/api/v1/batches/", {"name": "Test Batch", "template": template.id, "participant_file": csv_file}, format="multipart")
    batch_id = resp_batch.data["id"]
    
    auth_client.post(f"/api/v1/batches/{batch_id}/validate/")
    
    resp_gen = auth_client.post(f"/api/v1/batches/{batch_id}/generate/")
    assert resp_gen.status_code == status.HTTP_202_ACCEPTED
    assert resp_gen.data["detail"] == "Batch queued for asynchronous generation."
    
    # Assert celery task was called
    mock_delay.assert_called_once_with(str(batch_id))


@pytest.mark.django_db
def test_validation_errors(auth_client, user, sample_image, temp_media):
    """Test batch validation with invalid CSV data"""
    from apps.templates_mgmt.models import CertificateTemplate
    
    img_file = SimpleUploadedFile("template.png", sample_image().read(), content_type="image/png")
    template = CertificateTemplate.objects.create(
        owner=user, name="Test", template_file=img_file,
        field_configuration={}, width=800, height=600
    )
    
    # CSV missing required 'name' column
    bad_csv_content = b"email,course_name\ntest@example.com,Python"
    bad_csv = SimpleUploadedFile("bad.csv", bad_csv_content, content_type="text/csv")
    
    resp_batch = auth_client.post("/api/v1/batches/", {"name": "Bad Batch", "template": template.id, "participant_file": bad_csv}, format="multipart")
    batch_id = resp_batch.data["id"]
    
    val_resp = auth_client.post(f"/api/v1/batches/{batch_id}/validate/")
    assert val_resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Missing required column" in str(val_resp.data)
