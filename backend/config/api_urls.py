"""Versioned API routes (``/api/v1/``).

Every domain app registers its viewset on a single DRF ``DefaultRouter`` so the
public surface is consistent (UUID lookups, pagination, browsable API). A few
function endpoints sit outside the router: auth (``login``/``me``), the health
probe, and the SSE event stream (a streaming response, not a REST resource).
"""
from django.http import JsonResponse
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.api import login, me
from apps.actors.api import ActorViewSet
from apps.agents.api import AgentViewSet, KnowledgeSourceViewSet, MemoryEntryViewSet
from apps.artifacts.api import ArtifactViewSet
from apps.audit.api import AuditLogViewSet, EventViewSet, stream_events
from apps.communications.api import ConversationViewSet
from apps.evaluations.api import EvaluationViewSet
from apps.executions.api import ExecutionViewSet, InterventionViewSet
from apps.models_registry.api import (
    CredentialViewSet,
    ModelProviderViewSet,
    ModelViewSet,
)
from apps.organizations.api import OrganizationViewSet
from apps.projects.api import ProjectViewSet, TaskViewSet
from apps.prompts.api import PromptViewSet
from apps.structure.api import CapabilityViewSet, OrgUnitViewSet, RoleViewSet
from apps.workflows.api import ArenaViewSet, WorkflowLinkViewSet, WorkflowViewSet


def health(_request):
    return JsonResponse({"status": "ok", "service": "easyes", "version": "v1"})


router = DefaultRouter()
router.register("organizations", OrganizationViewSet, basename="organization")
router.register("capabilities", CapabilityViewSet, basename="capability")
router.register("units", OrgUnitViewSet, basename="orgunit")
router.register("roles", RoleViewSet, basename="role")
router.register("actors", ActorViewSet, basename="actor")
router.register("agents", AgentViewSet, basename="agent")
router.register("knowledge-sources", KnowledgeSourceViewSet, basename="knowledge-source")
router.register("memory", MemoryEntryViewSet, basename="memory-entry")
router.register("providers", ModelProviderViewSet, basename="provider")
router.register("models", ModelViewSet, basename="model")
router.register("credentials", CredentialViewSet, basename="credential")
router.register("prompts", PromptViewSet, basename="prompt")
router.register("workflows", WorkflowViewSet, basename="workflow")
router.register("arenas", ArenaViewSet, basename="arena")
router.register("workflow-links", WorkflowLinkViewSet, basename="workflow-link")
router.register("projects", ProjectViewSet, basename="project")
router.register("tasks", TaskViewSet, basename="task")
router.register("executions", ExecutionViewSet, basename="execution")
router.register("interventions", InterventionViewSet, basename="intervention")
router.register("conversations", ConversationViewSet, basename="conversation")
router.register("artifacts", ArtifactViewSet, basename="artifact")
router.register("evaluations", EvaluationViewSet, basename="evaluation")
router.register("events", EventViewSet, basename="event")
router.register("audit-logs", AuditLogViewSet, basename="auditlog")


urlpatterns = [
    path("health/", health, name="health"),
    path("auth/login/", login, name="auth-login"),
    path("auth/me/", me, name="auth-me"),
    path("executions/<uuid:uuid>/stream/", stream_events, name="execution-stream"),
    path("", include(router.urls)),
]
