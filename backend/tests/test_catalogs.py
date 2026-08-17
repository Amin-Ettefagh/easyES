from __future__ import annotations

import pytest

from core.provider_catalog import provider_catalog
from core.taxonomy_import import TaxonomyRole, merged_taxonomy


def test_provider_catalog_contains_every_requested_and_local_provider():
    entries = provider_catalog()
    assert len([entry for entry in entries if not entry["local"]]) == 148
    assert len([entry for entry in entries if entry["local"]]) == 7
    keys = {entry["key"] for entry in entries}
    assert {"openai", "anthropic", "amazon-bedrock", "ollama-local", "custom-rest"} <= keys


def test_taxonomies_merge_without_duplicate_normalized_roles():
    roles = merged_taxonomy()
    assert len(roles) == 2785
    assert len({role.name.casefold() for role in roles}) == len(roles)
    assert all(role.category for role in roles)


@pytest.mark.django_db
def test_role_import_creates_agent_actor_without_prompt(monkeypatch, demo_org):
    from apps.actors.models import RoleAssignment
    from apps.agents.models import Agent
    from core import taxonomy_import

    organization = demo_org
    monkeypatch.setattr(taxonomy_import, "merged_taxonomy", lambda: [
        TaxonomyRole("Synthetic Reliability Lead", "Reliability", {"test"}),
        TaxonomyRole("Synthetic Release Manager", "Delivery", {"test"}),
    ])
    result = taxonomy_import.import_role_agents(organization)
    assert result["agents_created"] == 2
    agents = Agent.objects.filter(organization=organization, config__taxonomy_seed=True)
    assert agents.count() == 2
    assert all(not agent.prompt_assignments.exists() for agent in agents)
    assert RoleAssignment.objects.filter(actor__agent__in=agents).count() == 2

    second = taxonomy_import.import_role_agents(organization)
    assert second["roles_created"] == 0
    assert second["agents_created"] == 0
