"""
Standard pagination classes for the API.
"""
from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Default pagination: 20 items per page, max 100."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class LargePagination(PageNumberPagination):
    """For endpoints that return larger lists (e.g., certificates in a batch)."""

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200
