import secrets
import string
from datetime import datetime
from django.conf import settings


def generate_certificate_id():
    """
    Generates a unique, human-readable, and collision-resistant certificate ID.
    Format: {PREFIX}-{YEAR}-{6_RANDOM_ALPHANUMERIC}
    Example: CERT-2026-A1B2C3
    """
    prefix = settings.CERTIFICATE_ID_PREFIX
    year = datetime.now().year
    
    # Generate 6 random alphanumeric characters (excluding confusing characters like O, 0, I, l, 1)
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    random_part = "".join(secrets.choice(alphabet) for _ in range(6))
    
    return f"{prefix}-{year}-{random_part}"
