"""Idempotent demo seed for the ``amin`` software company.

This module builds, from data only, everything the Definition of Done needs:
the demo login, the Organization, its org-units/roles/capabilities, a Fake model
provider + model + credential, versioned prompts, one specialized Agent per
lifecycle stage (each wired to a Role, an Actor, a Model and a system prompt),
and the software-development Workflow graph whose QA gate contains a *real* loop
(fail → fix → re-develop → retest → pass) with safety limits.

Nothing here is hard-coded into the Core engine — the engine only ever reads the
rows this seed writes, which is the whole point of the decoupled design
(Idea.md §72, DemoPrompt DoD). Every step is ``get_or_create`` so re-running is
safe.
"""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction

DEMO_ORG_SLUG = "amin"
DEMO_USER = "amin"
DEMO_PASSWORD = "123456"


# --- capabilities, roles, stages -----------------------------------------
CAPABILITIES = [
    ("analysis", "Analysis"),
    ("research", "Research"),
    ("product", "Product Management"),
    ("architecture", "Architecture"),
    ("coding", "Coding"),
    ("testing", "Testing"),
    ("review", "Review"),
    ("delivery", "Delivery"),
]

# (role_key, role_name, unit_key, capability_key, agent_stage or None)
# product_owner is intentionally agent-less: it is the *human* role held by the
# demo user (amin). The "Idea Analysis" node therefore runs as an agent-less
# deterministic stage (the engine supports this) — a clean Role≠Actor≠Agent
# illustration: a Role, performed by a human Actor, with no AI Agent.
ROLES = [
    ("product_owner", "Product Owner", "product", "analysis", None),
    ("market_researcher", "Market Researcher", "product", "research", "market_research"),
    ("product_manager", "Product Manager", "product", "product", "product_spec"),
    ("software_architect", "Software Architect", "engineering", "architecture", "architecture"),
    ("backend_engineer", "Backend Engineer", "engineering", "coding", "backend_implementation"),
    ("frontend_engineer", "Frontend Engineer", "engineering", "coding", "frontend_implementation"),
    ("integration_engineer", "Integration Engineer", "engineering", "coding", "integration"),
    ("qa_engineer", "QA Engineer", "quality", "testing", "qa"),
    ("tech_lead", "Tech Lead", "engineering", "review", "fix_planning"),
    ("code_reviewer", "Code Reviewer", "quality", "review", "review"),
    ("delivery_lead", "Delivery Lead", "delivery", "delivery", "final_evaluation"),
]

UNITS = [
    ("product", "Product", "department"),
    ("engineering", "Engineering", "department"),
    ("quality", "Quality Assurance", "department"),
    ("delivery", "Delivery", "department"),
]

# System-prompt text per stage (kept short; editable in the UI afterwards).
STAGE_PROMPTS = {
    "idea_analysis": "You are a Product Owner. Analyze the idea for feasibility and scope.",
    "market_research": "You are a Market Researcher. Assess the market, competitors and positioning.",
    "product_spec": "You are a Product Manager. Produce a prioritized feature list and product spec.",
    "architecture": "You are a Software Architect. Design a simple architecture and API contract.",
    "backend_implementation": "You are a Backend Engineer. Implement the API to the contract exactly.",
    "frontend_implementation": "You are a Frontend Engineer. Build the UI against the API contract.",
    "integration": "You are an Integration Engineer. Integrate backend and frontend.",
    "qa": "You are a QA Engineer. Test against the contract and report pass/fail with evidence.",
    "fix_planning": "You are a Tech Lead. Diagnose the QA failure and produce a targeted fix plan.",
    "review": "You are a Code Reviewer. Review the code against a checklist and approve or reject.",
    "final_evaluation": "You are the Delivery Lead. Confirm completion criteria and write the final report.",
}


@transaction.atomic
def seed_demo(*, create_user: bool = True):
    """Create (or update) the demo organization and everything under it.

    Returns the :class:`~apps.organizations.models.Organization`.
    """
    from apps.organizations.models import Membership, Organization

    user = _seed_user() if (create_user and settings.ALLOW_DEMO_SEED) else None

    org, _ = Organization.objects.get_or_create(
        slug=DEMO_ORG_SLUG,
        defaults={
            "name": "amin",
            "type": Organization.Type.SOFTWARE_COMPANY,
            "description": "Demo software company running an AI-driven delivery lifecycle.",
            "owner": user,
        },
    )
    if user and org.owner_id is None:
        org.owner = user
        org.save(update_fields=["owner"])
    if user:
        Membership.objects.get_or_create(
            organization=org, user=user,
            defaults={"level": Membership.Level.OWNER},
        )

    caps = _seed_capabilities(org)
    units = _seed_units(org)
    roles = _seed_roles(org, units, caps)
    model = _seed_model_stack(org)
    agents = _seed_agents(org, roles, model, caps)
    _seed_actors(org, roles, agents, user)
    workflow = _seed_workflow(org, agents)
    return org


def _seed_user():
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=DEMO_USER,
        defaults={"is_staff": True, "is_superuser": True, "is_demo": True,
                  "display_name": "Amin"},
    )
    if created:
        # Hashed via Django's password machinery — never stored in plain text.
        user.set_password(DEMO_PASSWORD)
        user.save()
    return user


def _seed_capabilities(org):
    from apps.structure.models import Capability

    out = {}
    for key, name in CAPABILITIES:
        cap, _ = Capability.objects.get_or_create(
            organization=org, key=key, defaults={"name": name}
        )
        out[key] = cap
    return out


def _seed_units(org):
    from apps.structure.models import OrgUnit

    out = {}
    for order, (key, name, kind) in enumerate(UNITS):
        unit, _ = OrgUnit.objects.get_or_create(
            organization=org, name=name,
            defaults={"kind": kind, "order": order},
        )
        out[key] = unit
    return out


def _seed_roles(org, units, caps):
    from apps.structure.models import Role

    out = {}
    for role_key, role_name, unit_key, cap_key, _stage in ROLES:
        role, _ = Role.objects.get_or_create(
            organization=org, key=role_key,
            defaults={"name": role_name, "unit": units.get(unit_key), "is_seed": True},
        )
        if cap_key in caps:
            role.capabilities.add(caps[cap_key])
        out[role_key] = role
    return out


def _seed_model_stack(org):
    from apps.models_registry.models import Credential, Model, ModelProvider

    provider, _ = ModelProvider.objects.get_or_create(
        organization=org, key="fake",
        defaults={"name": "Fake (offline)", "adapter": ModelProvider.Adapter.FAKE},
    )
    cred, _ = Credential.objects.get_or_create(provider=provider, label="default")
    if not cred._secret:
        cred.set_secret("not-a-real-key")
        cred.save()
    model, _ = Model.objects.get_or_create(
        organization=org, key="fake-1",
        defaults={
            "provider": provider, "name": "Fake Model 1",
            "context_window": 8192, "max_output_tokens": 2048,
            "input_cost_per_1k": Decimal("0.0005"),
            "output_cost_per_1k": Decimal("0.0015"),
        },
    )
    return model


def _seed_agents(org, roles, model, caps):
    from apps.agents.models import Agent
    from apps.prompts.models import AgentPromptAssignment, Prompt, PromptVersion

    out = {}
    for role_key, role_name, _unit, cap_key, stage in ROLES:
        if stage is None:
            continue
        role = roles[role_key]
        agent, _ = Agent.objects.get_or_create(
            organization=org, key=f"{role_key}_agent",
            defaults={
                "name": f"{role_name} Agent",
                "role": role,
                "model": model,
                "credential": model.provider.credentials.first(),
                "temperature": 0.5,
                "max_output_tokens": 1024,
                "token_budget": 0,
                "cost_budget": Decimal("0"),
                "status": Agent.Status.ACTIVE,
                "config": {"stage": stage},
            },
        )
        if cap_key in caps:
            agent.capabilities.add(caps[cap_key])

        prompt, _ = Prompt.objects.get_or_create(
            organization=org, key=f"{role_key}_system",
            defaults={"name": f"{role_name} System Prompt", "kind": Prompt.Kind.SYSTEM},
        )
        version = prompt.versions.order_by("-version").first()
        if version is None:
            version = PromptVersion.objects.create(
                prompt=prompt, version=1, content=STAGE_PROMPTS[stage], is_active=True
            )
        AgentPromptAssignment.objects.get_or_create(
            agent=agent, kind="system",
            defaults={"prompt": prompt, "version": version},
        )
        out[stage] = agent
    return out


def _seed_actors(org, roles, agents, user):
    from apps.actors.models import Actor, RoleAssignment

    # One human actor (amin) tied to the product owner role.
    if user is not None:
        human, _ = Actor.objects.get_or_create(
            organization=org, name="Amin", kind=Actor.Kind.HUMAN,
            defaults={"user": user},
        )
        RoleAssignment.objects.get_or_create(actor=human, role=roles["product_owner"])

    # One ai_agent actor per agent, tied back to the Agent (Actor.agent OneToOne).
    for stage, agent in agents.items():
        actor, _ = Actor.objects.get_or_create(
            organization=org, agent=agent,
            defaults={"name": agent.name, "kind": Actor.Kind.AI_AGENT},
        )
        if agent.role_id:
            RoleAssignment.objects.get_or_create(actor=actor, role=agent.role)


# --- the workflow graph (with the real QA loop) --------------------------
def _seed_workflow(org, agents):
    from apps.workflows.models import Edge, Node, Workflow

    wf, created = Workflow.objects.get_or_create(
        organization=org, key="software_delivery", version=1,
        defaults={
            "name": "Software Delivery Lifecycle",
            "description": (
                "Idea → Research → Planning → Development → Testing → Review → "
                "Improvement → Completion, with a QA fix loop."
            ),
            "status": Workflow.Status.PUBLISHED,
        },
    )
    if not created and wf.nodes.exists():
        return wf  # already built

    def node(key, name, ntype, *, agent_stage=None, config=None, x=0, y=0):
        return Node.objects.create(
            workflow=wf, key=key, name=name, type=ntype,
            agent=agents.get(agent_stage) if agent_stage else None,
            role=agents[agent_stage].role if agent_stage and agents.get(agent_stage) else None,
            config=config or ({"stage": agent_stage} if agent_stage else {}),
            position_x=x, position_y=y,
        )

    n_start = node("start", "Start", Node.Type.START, x=0, y=0)
    n_idea = node("idea", "Idea Analysis", Node.Type.AGENT_TASK, agent_stage="idea_analysis", x=180, y=0)
    n_market = node("market", "Market Research", Node.Type.AGENT_TASK, agent_stage="market_research", x=360, y=0)
    n_product = node("product", "Product Spec", Node.Type.AGENT_TASK, agent_stage="product_spec", x=540, y=0)
    n_arch = node("architecture", "Architecture", Node.Type.AGENT_TASK, agent_stage="architecture", x=720, y=0)
    n_backend = node("backend", "Backend Implementation", Node.Type.AGENT_TASK, agent_stage="backend_implementation", x=900, y=0)
    n_frontend = node("frontend", "Frontend Implementation", Node.Type.AGENT_TASK, agent_stage="frontend_implementation", x=1080, y=0)
    n_integration = node("integration", "Integration", Node.Type.AGENT_TASK, agent_stage="integration", x=1260, y=0)
    n_qa = node("qa", "QA Testing", Node.Type.EVALUATION, agent_stage="qa",
                config={"stage": "qa", "coverage_threshold": 0.8}, x=1440, y=0)
    n_gate = node("qa_gate", "QA Gate", Node.Type.DECISION, config={
        "loop": True,
        "loop_back_label": "fail",
        "give_up_label": "give_up",
        "max_iterations": 5,
        "max_cost": 0,
        "max_duration_seconds": 0,
        "failure_threshold": 0,
    }, x=1620, y=0)
    n_fix = node("fix_planning", "Fix Planning", Node.Type.AGENT_TASK, agent_stage="fix_planning", x=1440, y=180)
    n_review = node("review", "Code Review", Node.Type.REVIEW, agent_stage="review", x=1800, y=0)
    n_final = node("final", "Final Evaluation", Node.Type.AGENT_TASK, agent_stage="final_evaluation", x=1980, y=0)
    n_archive = node("archive", "Complete / Archive", Node.Type.ARCHIVE, x=2160, y=0)
    n_giveup = node("giveup_archive", "Archive (failed)", Node.Type.ARCHIVE, x=1800, y=180)

    def edge(src, tgt, *, label="", condition="", order=0):
        Edge.objects.create(workflow=wf, source=src, target=tgt,
                            label=label, condition=condition, order=order)

    edge(n_start, n_idea)
    edge(n_idea, n_market)
    edge(n_market, n_product)
    edge(n_product, n_arch)
    edge(n_arch, n_backend)
    edge(n_backend, n_frontend)
    edge(n_frontend, n_integration)
    edge(n_integration, n_qa)
    edge(n_qa, n_gate)
    # QA gate branches — order matters: pass/fail are checked before give_up.
    edge(n_gate, n_review, label="pass", condition="evaluation.passed == True", order=0)
    edge(n_gate, n_fix, label="fail", condition="evaluation.passed == False", order=1)
    edge(n_gate, n_giveup, label="give_up", order=2)
    # Loop back: fix → re-develop → re-integrate → retest.
    edge(n_fix, n_backend)
    edge(n_review, n_final)
    edge(n_final, n_archive)
    return wf


@transaction.atomic
def create_demo_project(org, *, key="taskflow", name="TaskFlow — Team Task Manager",
                        idea=None, scenario="fail_once"):
    """Create a runnable demo :class:`~apps.projects.models.Project` bound to the
    seeded workflow. Returns the Project."""
    from apps.projects.models import Project
    from apps.workflows.models import Workflow

    workflow = Workflow.objects.filter(organization=org, key="software_delivery").first()
    project, _ = Project.objects.get_or_create(
        organization=org, key=key,
        defaults={
            "name": name,
            "workflow": workflow,
            "idea": idea or "A lightweight task manager for small teams.",
            "requirements": [
                "Email/password auth", "Projects", "Tasks with status",
                "Assign task to member", "Board view",
            ],
            "status": Project.Status.ACTIVE,
            "workspace_key": f"{org.slug}-{key}",
            "context": {"scenario": scenario},
        },
    )
    return project
