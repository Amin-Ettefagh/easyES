"""Shared abstract model bases used across apps.

Lives in ``core`` (not an app) so every app can import it without creating a
dependency between apps. These are abstract — they create no tables.
"""
from __future__ import annotations

import uuid

from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class UUIDModel(models.Model):
    """Public-facing UUID id. We keep BigAuto pk for FK speed and add a stable
    ``uuid`` for external references / URLs."""

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimeStampedModel):
    class Meta:
        abstract = True
        ordering = ["-created_at"]
