"""Parse the two role taxonomies and idempotently provision one agent per role."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils.text import slugify


@dataclass
class TaxonomyRole:
    name: str
    category: str
    sources: set[str] = field(default_factory=set)


def normalize_role_name(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).strip()
    value = re.sub(r"\s*[—–-]\s*[A-Z][A-Z0-9/&+.-]{1,12}$", "", value)
    value = re.sub(r"\s*\(([A-Z][A-Z0-9/&+.-]{1,12})\)\s*$", "", value)
    value = value.replace("&", " and ").casefold()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _catalog_path(filename: str) -> Path | None:
    candidates = [
        Path(settings.BASE_DIR) / "catalog" / filename,
        Path(settings.BASE_DIR).parent / filename,
        Path("/app/catalog") / filename,
    ]
    return next((path for path in candidates if path.exists()), None)


def parse_roll(path: Path) -> list[TaxonomyRole]:
    category = "Uncategorized"
    output = []
    heading = re.compile(r"^###\s+\d{2,3}\.\s+(.+?)\s*$")
    role = re.compile(r"^[│ ]*[├└]──\s+(.+?)\s*$")
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if match := heading.match(line):
            category = match.group(1).strip()
        elif match := role.match(line):
            output.append(TaxonomyRole(match.group(1).strip(), category, {"roll.md"}))
    return output


def parse_html(path: Path) -> list[TaxonomyRole]:
    text = path.read_text(encoding="utf-8-sig")
    match = re.search(r"const ROOT=(.*?);\s*const tree=", text, re.DOTALL)
    if not match:
        raise ValueError("SoftwareEngineerCompanySamples.html does not contain ROOT taxonomy JSON")
    root = json.loads(match.group(1))
    output = []

    def walk(node: dict, path_parts: list[str]):
        children = node.get("children") or []
        if not children:
            category = re.sub(r"^\d{2,3}\.\s*", "", path_parts[0]) if path_parts else "Uncategorized"
            output.append(TaxonomyRole(str(node["label"]).strip(), category, {"SoftwareEngineerCompanySamples.html"}))
            return
        for child in children:
            walk(child, [*path_parts, str(node.get("label", "")).strip()])

    for function in root.get("children", []):
        walk(function, [])
    return output


def merged_taxonomy() -> list[TaxonomyRole]:
    roles: dict[str, TaxonomyRole] = {}
    sources = [
        ("roll.md", parse_roll),
        ("SoftwareEngineerCompanySamples.html", parse_html),
    ]
    for filename, parser in sources:
        path = _catalog_path(filename)
        if not path:
            continue
        for item in parser(path):
            normalized = normalize_role_name(item.name)
            if not normalized:
                continue
            if normalized in roles:
                roles[normalized].sources.update(item.sources)
            else:
                roles[normalized] = item
    return sorted(roles.values(), key=lambda item: (item.category.casefold(), item.name.casefold()))


def _stable_key(name: str, suffix: str = "") -> str:
    normalized = normalize_role_name(name)
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:10]
    base = slugify(normalized) or "role"
    tail = f"-{suffix}" if suffix else ""
    return f"{base[: 80 - len(tail) - 11]}-{digest}{tail}"[:80]


@transaction.atomic
def import_role_agents(organization) -> dict:
    """Idempotently create categories, unique roles, agents, actors and assignments."""
    from apps.actors.models import Actor, RoleAssignment
    from apps.agents.models import Agent
    from apps.models_registry.models import Model
    from apps.structure.models import OrgUnit, Role

    taxonomy = merged_taxonomy()
    categories = sorted({item.category for item in taxonomy}, key=str.casefold)
    units_by_normalized = {normalize_role_name(unit.name): unit for unit in organization.units.all()}
    missing_units = [
        OrgUnit(organization=organization, name=name[:150], kind=OrgUnit.Kind.DEPARTMENT, order=index + 100)
        for index, name in enumerate(categories)
        if normalize_role_name(name) not in units_by_normalized
    ]
    OrgUnit.objects.bulk_create(missing_units, batch_size=500)
    units_by_normalized = {normalize_role_name(unit.name): unit for unit in organization.units.all()}

    existing_roles = list(organization.roles.select_related("unit").all())
    roles_by_normalized = {normalize_role_name(role.name): role for role in existing_roles}
    new_roles = []
    for item in taxonomy:
        normalized = normalize_role_name(item.name)
        if normalized in roles_by_normalized:
            continue
        new_roles.append(Role(
            organization=organization,
            unit=units_by_normalized.get(normalize_role_name(item.category)),
            key=_stable_key(item.name),
            name=item.name[:150],
            description=f"Taxonomy role in {item.category}. Sources: {', '.join(sorted(item.sources))}.",
            is_seed=True,
        ))
    Role.objects.bulk_create(new_roles, batch_size=500, ignore_conflicts=True)
    all_roles = list(organization.roles.select_related("unit").all())
    roles_by_normalized = {normalize_role_name(role.name): role for role in all_roles}

    represented_role_ids = set(organization.agents.exclude(role=None).values_list("role_id", flat=True))
    default_model = Model.objects.filter(organization=organization, provider__adapter="fake", is_active=True).first()
    new_agents = []
    for item in taxonomy:
        role = roles_by_normalized[normalize_role_name(item.name)]
        if role.id in represented_role_ids:
            continue
        key = _stable_key(item.name, "agent")
        new_agents.append(Agent(
            organization=organization,
            role=role,
            model=default_model,
            key=key,
            name=f"{role.name[:144]} Agent"[:150],
            description=f"Editable AI worker for the {role.name} role.",
            status=Agent.Status.ACTIVE,
            is_enabled=True,
            config={"taxonomy_seed": True, "category": item.category, "sources": sorted(item.sources)},
        ))
    Agent.objects.bulk_create(new_agents, batch_size=500, ignore_conflicts=True)

    taxonomy_role_ids = {roles_by_normalized[normalize_role_name(item.name)].id for item in taxonomy}
    agents = list(organization.agents.filter(role_id__in=taxonomy_role_ids))
    actor_agent_ids = set(organization.actors.exclude(agent=None).values_list("agent_id", flat=True))
    Actor.objects.bulk_create([
        Actor(
            organization=organization,
            kind=Actor.Kind.AI_AGENT,
            name=agent.name,
            agent=agent,
            presence=Actor.Presence.AVAILABLE,
            metadata={"taxonomy_seed": True},
        )
        for agent in agents if agent.id not in actor_agent_ids
    ], batch_size=500, ignore_conflicts=True)

    actors = list(organization.actors.filter(agent__role_id__in=taxonomy_role_ids).select_related("agent"))
    existing_assignments = set(RoleAssignment.objects.filter(actor__in=actors).values_list("actor_id", "role_id"))
    RoleAssignment.objects.bulk_create([
        RoleAssignment(actor=actor, role=actor.agent.role, is_primary=True)
        for actor in actors
        if actor.agent and actor.agent.role_id and (actor.id, actor.agent.role_id) not in existing_assignments
    ], batch_size=500, ignore_conflicts=True)

    return {
        "taxonomy_roles": len(taxonomy),
        "categories": len(categories),
        "roles_created": len(new_roles),
        "agents_created": len(new_agents),
        "total_roles": organization.roles.count(),
        "total_agents": organization.agents.count(),
    }
