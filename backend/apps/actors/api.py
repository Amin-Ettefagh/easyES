"""Actors API: the unified human / AI / system participants.

An Actor is *not* a Role and *not* an Agent (DemoPrompt decoupling rule):
it's the thing that actually performs work and holds role assignments.
"""
from __future__ import annotations

from rest_framework import serializers

from core.api_common import OrgScopedViewSet, current_org_id
from apps.actors.models import Actor, RoleAssignment


class RoleAssignmentSerializer(serializers.ModelSerializer):
    role_key = serializers.CharField(source="role.key", read_only=True, default="")
    role_name = serializers.CharField(source="role.name", read_only=True, default="")

    class Meta:
        model = RoleAssignment
        fields = ["uuid", "role", "role_key", "role_name", "is_primary"]


class ActorSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True, default="")
    agent_key = serializers.CharField(source="agent.key", read_only=True, default="")
    role_assignments = RoleAssignmentSerializer(many=True, read_only=True)
    role_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)

    class Meta:
        model = Actor
        fields = [
            "uuid", "kind", "name", "presence", "user", "username", "agent_key",
            "role_assignments", "role_ids", "metadata", "created_at",
        ]
        read_only_fields = ["uuid", "agent_key", "role_assignments", "created_at"]

    def create(self, validated_data):
        role_ids = validated_data.pop("role_ids", [])
        actor = super().create(validated_data)
        for role_id in role_ids:
            RoleAssignment.objects.create(actor=actor, role_id=role_id, is_primary=not actor.role_assignments.exists())
        return actor

    def update(self, instance, validated_data):
        role_ids = validated_data.pop("role_ids", None)
        actor = super().update(instance, validated_data)
        if role_ids is not None:
            actor.role_assignments.all().delete()
            for index, role_id in enumerate(role_ids):
                RoleAssignment.objects.create(actor=actor, role_id=role_id, is_primary=index == 0)
        return actor


class ActorViewSet(OrgScopedViewSet):
    queryset = (
        Actor.objects.select_related("user", "agent")
        .prefetch_related("role_assignments__role")
        .all()
    )
    serializer_class = ActorSerializer

    def perform_create(self, serializer):
        from apps.organizations.models import Membership
        from apps.structure.models import Role

        org_id = current_org_id(self.request)
        kind = serializer.validated_data.get("kind")
        user = serializer.validated_data.get("user")
        role_ids = serializer.validated_data.get("role_ids", [])
        if kind not in {Actor.Kind.HUMAN, Actor.Kind.HYBRID}:
            raise serializers.ValidationError({"kind": "Create AI actors through the Agent screen."})
        if user and not Membership.objects.filter(organization_id=org_id, user=user).exists():
            raise serializers.ValidationError({"user": "User is not a member of this company."})
        if Role.objects.filter(id__in=role_ids).exclude(organization_id=org_id).exists():
            raise serializers.ValidationError({"role_ids": "Every role must belong to this company."})
        serializer.save(organization_id=org_id)
