import os
import pytest
from django.conf import settings
from PIL import Image
from services.pdf_generator import PDFGenerator
from services.certificate_id import generate_certificate_id


@pytest.mark.django_db
def test_generate_certificate_id():
    cert_id = generate_certificate_id()
    assert cert_id.startswith(settings.CERTIFICATE_ID_PREFIX)
    # format CERT-YYYY-XXXXXX
    parts = cert_id.split("-")
    assert len(parts) == 3
    assert len(parts[2]) == 6


@pytest.mark.django_db
def test_pdf_generator(tmp_path):
    # 1. Create a dummy image
    img_path = tmp_path / "template.png"
    img = Image.new("RGB", (800, 600), color="white")
    img.save(img_path)
    
    # 2. Prepare data
    participant = {
        "name": "Test User",
        "email": "test@example.com",
        "course_name": "Testing 101"
    }
    field_config = {
        "name": {"x": 400, "y": 300, "font_size": 24, "align": "center"}
    }
    
    # 3. Generate
    pdf_gen = PDFGenerator()
    buffer, cert_id = pdf_gen.generate(str(img_path), participant, field_config)
    
    # 4. Verify
    assert buffer is not None
    assert buffer.getvalue().startswith(b"%PDF-")
    assert cert_id is not None
    # The generator no longer mutates the caller's dict
    assert "certificate_id" not in participant
