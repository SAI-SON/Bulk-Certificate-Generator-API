"""
Shared pytest fixtures for all tests.
"""
import io
import os
import tempfile

import pytest
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from PIL import Image


@pytest.fixture
def api_client():
    """Unauthenticated DRF test client."""
    return APIClient()


@pytest.fixture
def create_user(db):
    """Factory fixture to create users."""
    def _create_user(username="testuser", password="TestPass123!", email="test@example.com", **kwargs):
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            **kwargs,
        )
        return user
    return _create_user


@pytest.fixture
def user(create_user):
    """A default test user."""
    return create_user()


@pytest.fixture
def another_user(create_user):
    """A second test user for cross-user access tests."""
    return create_user(
        username="otheruser",
        email="other@example.com",
    )


@pytest.fixture
def auth_client(user):
    """Authenticated DRF test client with token auth."""
    client = APIClient()
    token, _ = Token.objects.get_or_create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.fixture
def another_auth_client(another_user):
    """Authenticated DRF test client for the second user."""
    client = APIClient()
    token, _ = Token.objects.get_or_create(user=another_user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.fixture
def sample_image():
    """Create a sample PNG image in memory for template upload tests."""
    def _create_image(width=800, height=600, color="white", fmt="PNG"):
        img = Image.new("RGB", (width, height), color=color)
        buffer = io.BytesIO()
        img.save(buffer, format=fmt)
        buffer.seek(0)
        buffer.name = f"test_template.{fmt.lower()}"
        return buffer
    return _create_image


@pytest.fixture
def sample_csv():
    """Create a sample CSV file in memory."""
    def _create_csv(rows=None):
        if rows is None:
            rows = [
                "name,email,course_name,completion_date",
                "Arun,arun@example.com,Python Workshop,2026-10-01",
                "Priya,priya@example.com,Python Workshop,2026-10-01",
                "Kumar,kumar@example.com,Python Workshop,2026-10-01",
            ]
        content = "\n".join(rows)
        buffer = io.BytesIO(content.encode("utf-8"))
        buffer.name = "participants.csv"
        return buffer
    return _create_csv


@pytest.fixture
def temp_media(settings, tmp_path):
    """Override MEDIA_ROOT to use a temporary directory for tests."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    return settings.MEDIA_ROOT
