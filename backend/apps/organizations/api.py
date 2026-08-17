"""Organizations API: read the company and its membership."""
from __future__ import annotations

from django.db import transaction
from django.db.models import Q
from django.utils.text import slugify
from rest_framework import serializers

from core.api_common import OrgScopedViewSet, user_org_ids
from apps.organizations.models import Membership, Organization


class OrganizationSerializer(serializers.ModelSerializer):
    role_count = serializers.IntegerField(source="roles.count", read_only=True)
    agent_count = serializers.IntegerField(source="agents.count", read_only=True)
    project_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "uuid", "name", "slug", "type", "description", "is_active",
            "role_count", "agent_count", "project_count", "created_at",
        ]
        read_only_fields = ["uuid", "slug", "created_at"]

    def get_project_count(self, obj):
        return obj.projects.filter(
            Q(context__is_workflow_test=False)
            | ~Q(context__has_key="is_workflow_test")
        ).count()


class MembershipSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Membership
        fields = ["uuid", "username", "level", "created_at"]


class OrganizationViewSet(OrgScopedViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    org_field = "id"  # the object *is* the organization

    def get_queryset(self):
        # Company switching needs the complete membership list even while all
        # other resources are narrowed by X-Organization.
        return Organization.objects.filter(id__in=user_org_ids(self.request.user))

    @transaction.atomic
    def perform_create(self, serializer):
        base = slugify(serializer.validated_data.get("name", "company"))[:190] or "company"
        slug = base
        counter = 2
        while Organization.objects.filter(slug=slug).exists():
            slug = f"{base[:184]}-{counter}"
            counter += 1
        organization = serializer.save(owner=self.request.user, slug=slug)
        Membership.objects.create(
            organization=organization,
            user=self.request.user,
            level=Membership.Level.OWNER,
        )
