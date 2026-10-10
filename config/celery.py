"""
Celery application configuration for Bulk Certificate Generator API.

This module is imported by config/__init__.py so that Celery is available
when Django starts.
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("certgen")

# Read Celery config from Django settings, using the CELERY_ namespace.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all installed apps and the tasks/ package.
app.autodiscover_tasks(["tasks"])
