"""API tests: auth, multi-tenant scoping, the DoD prompt-edit action, and the
``start`` action that runs a real execution through the engine.

These exercise the DRF surface the frontend depends on. Execution runs inline
(see conftest) so the ``start`` endpoint returns a finished run synchronously.
"""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

API = "/api/v1"


@pytest.fixture
def seeded(db):
    """Seed the demo company *with* the amin user + membership so org-scoped
    endpoints return rows for that user."""
    from core.seed import seed_demo

    org = seed_demo(create_user=True)
    from apps.accounts.models import User

    return org, User.objects.get(username="amin")


@pytest.fixture
def api(seeded):
    org, user = seeded
    client = APIClient()
    client.force_authenticate(user=user)
    return client, org, user


def test_login_returns_token_and_user():
    from core.seed import seed_demo

    seed_demo(create_user=True)
    client = APIClient()
    resp = client.post(
        f"{API}/auth/login/", {"username": "amin", "password": "123456"}, format="json"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access"]
    assert body["refresh"]
    assert body["user"]["username"] == "amin"
    assert any(o["slug"] == "amin" for o in body["user"]["organizations"])


def test_login_rejects_bad_password():
    from core.seed import seed_demo

    seed_demo(create_user=True)
    client = APIClient()
    resp = client.post(
        f"{API}/auth/login/", {"username": "amin", "password": "wrong"}, format="json"
    )
    assert resp.status_code == 401


def test_user_can_create_and_select_multiple_companies(api):
    client, first_org, user = api
    created = client.post(
        f"{API}/organizations/",
        {"name": "Second Company", "type": "startup", "description": "Tenant isolation test"},
        format="json",
    )
    assert created.status_code == 201, created.json()
    second_uuid = created.json()["uuid"]
    client.credentials(HTTP_X_ORGANIZATION=second_uuid)
    workflow = client.post(f"{API}/workflows/", {"name": "Second company flow"}, format="json")
    assert workflow.status_code == 201, workflow.json()
    from apps.workflows.models import Workflow

    assert Workflow.objects.get(uuid=workflow.json()["uuid"]).organization.uuid == __import__("uuid").UUID(second_uuid)
    companies = client.get(f"{API}/organizations/")
    assert companies.status_code == 200
    assert companies.json()["count"] >= 2


def test_unauthenticated_is_rejected():
    client = APIClient()
    resp = client.get(f"{API}/agents/")
    assert resp.status_code in (401, 403)


def test_agents_list_is_org_scoped(api):
    client, org, _ = api
    resp = client.get(f"{API}/agents/")
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 10
    keys = {a["key"] for a in results}
    assert "backend_engineer_agent" in keys
    # Each agent exposes its resolved system prompt + editable knobs (DoD §11).
    backend = next(a for a in results if a["key"] == "backend_engineer_agent")
    assert backend["system_prompt"]
    assert "temperature" in backend and "max_output_tokens" in backend


def test_edit_agent_prompt_creates_new_version(api):
    client, org, _ = api
    from apps.agents.models import Agent

    agent = Agent.objects.get(organization=org, key="backend_engineer_agent")
    before = agent.prompt_assignments.get(kind="system").resolve_version().version

    resp = client.patch(
        f"{API}/agents/{agent.uuid}/prompt/",
        {"content": "You are the backend engineer. Follow the API contract exactly."},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["version"] == before + 1

    agent.refresh_from_db()
    after = agent.prompt_assignments.get(kind="system").resolve_version()
    assert after.version == before + 1
    assert "contract exactly" in after.content


def test_workflow_graph_endpoint_returns_nodes_and_edges(api):
    client, org, _ = api
    from apps.workflows.models import Workflow

    wf = Workflow.objects.get(organization=org, key="software_delivery")
    resp = client.get(f"{API}/workflows/{wf.uuid}/")
    assert resp.status_code == 200
    body = resp.json()
    node_keys = {n["key"] for n in body["nodes"]}
    assert {"start", "qa", "qa_gate", "fix_planning", "archive"} <= node_keys
    # The loop-back edge and the pass/fail branches are present in the graph.
    labels = {(e["source_key"], e["target_key"], e["label"]) for e in body["edges"]}
    assert ("qa_gate", "fix_planning", "fail") in labels
    assert ("fix_planning", "backend", "") in labels


def test_start_execution_runs_the_loop(api):
    client, org, user = api
    from core.seed import create_demo_project

    project = create_demo_project(org, key="api-demo", scenario="fail_once")

    resp = client.post(
        f"{API}/executions/start/",
        {"project": str(project.uuid), "scenario": "fail_once"},
        format="json",
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "succeeded"
    assert body["stop_reason"] == "pass"
    # The loop is visible in the response: node runs + loop state.
    assert any(nr["node_key"] == "fix_planning" for nr in body["node_runs"])
    loop = body["loop_states"][0]
    assert loop["iteration"] == 1


def test_events_endpoint_lists_run_timeline(api):
    client, org, user = api
    from core.seed import create_demo_project
    from core.workflow_engine import start_execution

    project = create_demo_project(org, key="events-demo", scenario="success")
    execution = start_execution(project, scenario="success", backend="inline")

    resp = client.get(f"{API}/events/?execution={execution.uuid}")
    assert resp.status_code == 200
    types = {e["type"] for e in resp.json()["results"]}
    assert "execution.started" in types


def test_create_agent_builds_actor_role_and_prompt(api):
    client, org, _ = api
    from apps.actors.models import Actor
    from apps.structure.models import Role

    role = Role.objects.get(organization=org, key="backend_engineer")
    response = client.post(
        f"{API}/agents/",
        {
            "name": "Platform Reliability Agent",
            "key": "platform_reliability_agent",
            "description": "Owns runtime reliability checks.",
            "role": role.pk,
            "temperature": 0.2,
            "max_output_tokens": 1200,
            "initial_prompt": "You are a reliability engineer. Always return evidence.",
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["key"] == "platform_reliability_agent"
    assert "reliability engineer" in body["system_prompt"]
    actor = Actor.objects.get(agent__uuid=body["uuid"])
    assert actor.organization == org
    assert actor.role_assignments.get().role == role


def test_agent_runtime_test_calls_selected_model(api):
    client, org, _ = api
    from apps.models_registry.models import Model

    model = Model.objects.filter(organization=org, provider__adapter="fake").first()
    response = client.post(
        f"{API}/agents/test-runtime/",
        {
            "model": model.pk,
            "prompt": "You are a runtime smoke-test agent.",
            "input": "Confirm readiness.",
            "temperature": 0,
            "max_tokens": 64,
        },
        format="json",
    )
    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["ok"] is True
    assert body["adapter"] == "fake"
    assert body["model"]
    assert body["latency_ms"] >= 0
    assert body["usage"]["total_tokens"] >= 0


def test_human_task_blocks_until_delivery_then_resumes(api):
    client, org, user = api
    from apps.executions.models import Intervention
    from apps.projects.models import Project, Task
    from apps.workflows.models import Edge, Node, Workflow
    from core.workflow_engine import WorkflowEngine, start_execution

    workflow = Workflow.objects.create(organization=org, key="human-gate-test", name="Human gate test")
    start = Node.objects.create(workflow=workflow, key="start", name="Start", type=Node.Type.START)
    human = Node.objects.create(workflow=workflow, key="human", name="Human design review", type=Node.Type.HUMAN_TASK, config={"prompt": "Review the design and attach a delivery note."})
    end = Node.objects.create(workflow=workflow, key="end", name="Done", type=Node.Type.END)
    Edge.objects.create(workflow=workflow, source=start, target=human, order=0)
    Edge.objects.create(workflow=workflow, source=human, target=end, order=1)
    project = Project.objects.create(organization=org, workflow=workflow, key="human-gate-project", name="Human gate project", workspace_key="human-gate-project")

    execution = start_execution(project, triggered_by=user, backend="inline")
    execution.refresh_from_db()
    assert execution.status == execution.Status.WAITING_FOR_APPROVAL
    gate = execution.interventions.get(kind=Intervention.Kind.HUMAN_TASK)
    assert gate.status == Intervention.Status.PENDING
    assert gate.task.status == Task.Status.BLOCKED

    gate.status = Intervention.Status.COMPLETED
    gate.response = "Design reviewed; accessibility checklist attached."
    gate.save(update_fields=["status", "response", "updated_at"])
    WorkflowEngine(execution).run()
    execution.refresh_from_db()
    assert execution.status == execution.Status.SUCCEEDED
    assert execution.node_runs.filter(node=human, status="succeeded").exists()


def test_workflow_studio_can_create_save_validate_and_test(api):
    client, org, _ = api

    created = client.post(
        f"{API}/workflows/",
        {"name": "Release smoke test", "key": "release-smoke", "status": "draft"},
        format="json",
    )
    assert created.status_code == 201, created.json()
    workflow_uuid = created.json()["uuid"]
    graph = {
        "name": "Release smoke test",
        "description": "Minimal executable workflow created by the studio.",
        "status": "draft",
        "nodes": [
            {"key": "start", "name": "Start", "type": "start", "position_x": 80, "position_y": 160, "config": {}},
            {"key": "finish", "name": "Complete", "type": "end", "position_x": 380, "position_y": 160, "config": {}},
        ],
        "edges": [
            {"source_key": "start", "target_key": "finish", "label": "", "condition": "", "order": 0},
        ],
    }
    saved = client.put(f"{API}/workflows/{workflow_uuid}/graph/", graph, format="json")
    assert saved.status_code == 200, saved.json()
    assert len(saved.json()["nodes"]) == 2
    assert len(saved.json()["edges"]) == 1

    valid = client.post(f"{API}/workflows/{workflow_uuid}/validate/", graph, format="json")
    assert valid.status_code == 200
    assert valid.json()["valid"] is True

    tested = client.post(
        f"{API}/workflows/{workflow_uuid}/test/",
        {"scenario": "success"},
        format="json",
    )
    assert tested.status_code == 201, tested.json()
    assert tested.json()["execution"]["status"] == "succeeded"


def test_project_lists_hide_only_workflow_test_runs(api):
    client, org, user = api
    from apps.projects.models import Project
    from apps.workflows.models import Workflow

    workflow = Workflow.objects.get(organization=org, key="software_delivery")
    Project.objects.create(
        organization=org,
        workflow=workflow,
        owner=user,
        key="visible-project",
        name="Visible project",
        context={"scenario": "success"},
    )
    Project.objects.create(
        organization=org,
        workflow=workflow,
        owner=user,
        key="studio-test-project",
        name="Workflow studio test",
        context={"is_workflow_test": True},
    )

    projects = client.get(f"{API}/projects/")
    assert projects.status_code == 200
    assert [item["key"] for item in projects.json()["results"]] == ["visible-project"]

    organization = client.get(f"{API}/organizations/{org.uuid}/")
    assert organization.status_code == 200
    assert organization.json()["project_count"] == 1


def test_provider_catalog_connects_encrypted_credential_and_remote_model(api):
    client, org, _ = api
    from apps.models_registry.models import Credential, ModelProvider

    catalog = client.get(f"{API}/providers/catalog/?search=ollama")
    assert catalog.status_code == 200
    assert any(item["key"] == "ollama-local" for item in catalog.json()["results"])

    connected = client.post(
        f"{API}/providers/connect/",
        {
            "catalog_key": "custom-openai-compatible",
            "key": "private-runtime",
            "name": "Private runtime",
            "base_url": "http://model-runtime.internal:9000/v1",
            "credentials": {"api_key": "never-return-this"},
            "model_id": "company/engineering-model:latest",
        },
        format="json",
    )
    assert connected.status_code == 201, connected.json()
    assert "never-return-this" not in str(connected.json())
    provider = ModelProvider.objects.get(organization=org, key="private-runtime")
    credential = Credential.objects.get(provider=provider)
    assert credential.get_secret_data()["api_key"] == "never-return-this"
    model = provider.models.get()
    assert model.remote_id == "company/engineering-model:latest"


def test_agent_credential_must_match_model_provider(api):
    client, org, _ = api
    from apps.models_registry.models import Credential, Model, ModelProvider

    fake_model = Model.objects.get(organization=org, key="fake-1")
    other = ModelProvider.objects.create(
        organization=org,
        key="other-provider",
        name="Other provider",
        adapter="openai_compatible",
        base_url="https://example.test/v1",
    )
    credential = Credential(provider=other, label="default")
    credential.set_secret_data({"api_key": "secret"})
    credential.save()
    response = client.post(
        f"{API}/agents/",
        {"name": "Invalid credential agent", "model": fake_model.pk, "credential": credential.pk},
        format="json",
    )
    assert response.status_code == 400
    assert "selected model provider" in str(response.json())
