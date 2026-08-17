"""Shared pytest fixtures for the whole suite.

All tests run against SQLite with ``inline`` execution so assertions see the
final state deterministically (no threads, no real model calls — the seeded
FakeModelProvider keeps everything offline).
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def force_inline_backend(settings):
    """Every execution started in tests runs synchronously in-process."""
    settings.EXECUTION_BACKEND = "inline"


@pytest.fixture
def demo_org(db):
    """The seeded ``amin`` demo company (org + roles + agents + workflow)."""
    from core.seed import seed_demo

    return seed_demo(create_user=False)


@pytest.fixture
def demo_user(db):
    from apps.accounts.models import User

    user, _ = User.objects.get_or_create(
        username="amin", defaults={"is_staff": True, "is_superuser": True}
    )
    return user


@pytest.fixture
def demo_project(db, demo_org):
    from core.seed import create_demo_project

    return create_demo_project(demo_org, scenario="success")


@pytest.fixture
def authenticated_client(client, demo_user):
    client.force_login(demo_user)
    return client
