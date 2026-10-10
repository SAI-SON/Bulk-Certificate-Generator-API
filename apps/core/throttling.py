"""
Custom throttling classes.
"""
from rest_framework.throttling import AnonRateThrottle


class VerificationRateThrottle(AnonRateThrottle):
    """
    Rate limit for the public certificate verification endpoint.
    Prevents abuse of the verification API.
    """

    scope = "verification"
