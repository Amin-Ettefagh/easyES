"""Shared DRF building blocks: multi-tenant scoping and base viewsets.

Every domain object hangs off an Organization. These mixins ensure a user only
ever sees rows for organizations they are a member of — multi-tenancy enforced
at the queryset level, not per-view (SECURITY.md, Idea.md multi-tenant-from-day-one).
"""
from __future__ import annotations

from uuid import UUID

from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated


def user_org_ids(user):
    """Organization ids this user may access (owner or member)."""
    if not user or not user.is_authenticated:
        return []
    if user.is_superuser:
        from apps.organizations.models import Organization

        return list(Organization.objects.values_list("id", flat=True))
    return list(user.memberships.values_list("organization_id", flat=True))


def current_org_id(request):
    """Resolve the tenant selected by the client.

    ``X-Organization`` accepts an organization UUID or slug. Keeping the
    selection in a header means every nested resource request is scoped the
    same way without leaking tenant ids into every URL. Older clients fall
    back to the first accessible organization.
    """
    from apps.organizations.models import Organization

    ids = user_org_ids(request.user)
    if not ids:
        raise serializers.ValidationError("No organization is available for this user.")
    selected = (request.headers.get("X-Organization") or request.query_params.get("organization") or "").strip()
    if selected:
        organizations = Organization.objects.filter(id__in=ids)
        organization = organizations.filter(slug=selected).first()
        if organization is None:
            try:
                organization = organizations.filter(uuid=UUID(selected)).first()
            except (ValueError, TypeError):
                organization = None
        if organization is None:
            raise serializers.ValidationError({"organization": "The selected organization is not available to this user."})
        return organization.id
    return ids[0]


class OrgScopedMixin:
    """Filters the queryset to the caller's organizations and uses the stable
    ``uuid`` as the URL lookup so internal ids are never exposed.

    Set ``org_field`` to the lookup path from the model to its Organization
    (default ``organization``).
    """

    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"
    org_field = "organization"

    def get_queryset(self):
        qs = super().get_queryset()
        ids = user_org_ids(self.request.user)
        selected = (self.request.headers.get("X-Organization") or self.request.query_params.get("organization") or "").strip()
        if selected:
            from apps.organizations.models import Organization

            organizations = Organization.objects.filter(id__in=ids)
            organization = organizations.filter(slug=selected).first()
            if organization is None:
                try:
                    organization = organizations.filter(uuid=UUID(selected)).first()
                except (ValueError, TypeError):
                    organization = None
            ids = [organization.id] if organization else []
        return qs.filter(**{f"{self.org_field}__in": ids})


class OrgScopedViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Full CRUD, org-scoped."""


class ReadOnlyOrgScopedViewSet(OrgScopedMixin, viewsets.ReadOnlyModelViewSet):
    """List + retrieve only, org-scoped. Genuinely read-only — no write actions
    are registered on the router."""
