"""Domain-model tests: the decoupling rules from Idea.md §72 / DemoPrompt.

These assert the *shape* of the domain, independent of any run: Role ≠ Actor ≠
Agent ≠ Model, Workflow ≠ Project ≠ Execution, and prompt versioning is
immutable. If the demo ever leaks into the Core these break.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.django_db


def test_seed_builds_full_company(demo_org):
    from apps.agents.models import Agent
    from apps.structure.models import Role
    from apps.workflows.models import Workflow

    assert demo_org.slug == "amin"
    assert Role.objects.filter(organization=demo_org).count() == 11
    # One agent per stage-bearing role (10 stages; product_owner has no agent).
    assert Agent.objects.filter(organization=demo_org).count() == 10
    wf = Workflow.objects.get(organization=demo_org, key="software_delivery")
    assert wf.status == Workflow.Status.PUBLISHED
    assert wf.start_node is not None


def test_role_actor_agent_model_are_distinct(demo_org):
    """A Role is the job, an Actor performs it, an Agent is the AI config, a
    Model is the inference source — four separate rows, linked not merged."""
    from apps.actors.models import Actor
    from apps.agents.models import Agent

    agent = Agent.objects.filter(organization=demo_org, key="backend_engineer_agent").first()
    assert agent is not None
    # Agent → Role (job) is a nullable FK, not identity.
    assert agent.role is not None
    assert agent.role.key == "backend_engineer"
    # Agent → Model (inference) is a separate object.
    assert agent.model is not None
    assert agent.model.key == "fake-1"
    # An AI Actor wraps the Agent; the Actor is not the Agent.
    actor = Actor.objects.get(agent=agent)
    assert actor.kind == Actor.Kind.AI_AGENT
    # Integer primary keys are scoped to their own tables and may legitimately
    # have the same value.  Distinct model types and globally unique UUIDs are
    # the meaningful proof that Actor and Agent are separate domain entities.
    assert actor._meta.label != agent._meta.label
    assert actor.uuid != agent.uuid


def test_workflow_project_execution_are_distinct(demo_org):
    from core.seed import create_demo_project
    from core.workflow_engine import start_execution

    project = create_demo_project(demo_org, scenario="success")
    # Project instantiates a Workflow; they are different objects.
    assert project.workflow is not None
    assert project.workflow.key == "software_delivery"

    execution = start_execution(project, scenario="success", backend="inline")
    # Execution is one run of the project; project holds durable outcome.
    assert execution.project_id == project.pk
    assert execution.workflow_id == project.workflow_id
    # Project and Execution live in separate tables, so comparing their local
    # integer PK values is not a valid identity check (both can be row 1).
    assert execution._meta.label != project._meta.label
    assert execution.uuid != project.uuid


def test_prompt_versions_are_immutable_history(demo_org):
    """Editing a prompt creates a new version; old versions are retained so past
    runs stay reproducible (DemoPrompt §11/§27)."""
    from apps.agents.models import Agent
    from apps.prompts.models import PromptVersion

    agent = Agent.objects.get(organization=demo_org, key="qa_engineer_agent")
    assignment = agent.prompt_assignments.get(kind="system")
    prompt = assignment.prompt
    v1 = prompt.active_version
    assert v1.version == 1

    v2 = PromptVersion.objects.create(
        prompt=prompt, version=2, content="Updated QA prompt.", is_active=True
    )
    prompt.versions.exclude(pk=v2.pk).update(is_active=False)

    # Both versions still exist; the old content is unchanged.
    assert prompt.versions.count() == 2
    assert PromptVersion.objects.get(pk=v1.pk).content != v2.content
    assert prompt.active_version.version == 2


def test_credential_secret_never_plaintext(demo_org):
    """Secrets are encrypted at rest and only ever exposed masked."""
    from apps.models_registry.models import Credential

    cred = Credential.objects.filter(provider__organization=demo_org).first()
    assert cred is not None
    # The stored column is not the plaintext.
    assert cred._secret != "not-a-real-key"
    assert cred._secret  # something is stored
    # But it round-trips through the decrypt helper.
    assert cred.get_secret() == "not-a-real-key"
