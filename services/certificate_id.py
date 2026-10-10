import secrets
from datetime import datetime
from django.conf import settings


def generate_certificate_id(max_retries=10):
    """
    Generates a unique, human-readable, and collision-resistant certificate ID.
    Format: {PREFIX}-{YEAR}-{6_RANDOM_ALPHANUMERIC}
    Example: CERT-2026-A1B2C3

    Retries up to ``max_retries`` times if the generated ID already exists in the
    database, avoiding IntegrityError on the unique constraint.
    """
    from apps.certificates.models import Certificate

    prefix = settings.CERTIFICATE_ID_PREFIX
    year = datetime.now().year
    
    # Exclude confusing characters like O, 0, I, l, 1
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

    for _ in range(max_retries):
        random_part = "".join(secrets.choice(alphabet) for _ in range(6))
        cert_id = f"{prefix}-{year}-{random_part}"

        if not Certificate.objects.filter(certificate_id=cert_id).exists():
            return cert_id

    # Extremely unlikely — exhausted retries
    raise RuntimeError(
        f"Failed to generate a unique certificate ID after {max_retries} attempts."
    )
