from rest_framework.throttling import AnonRateThrottle

class VerificationRateThrottle(AnonRateThrottle):
    """
    Custom throttle to limit public certificate verification endpoint.
    Prevents scraping of certificate IDs.
    """
    rate = "100/hour"
