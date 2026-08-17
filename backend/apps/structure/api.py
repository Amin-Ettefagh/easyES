"""Structure API: capabilities, org-units, and roles (the company shape)."""
from __future__ import annotations

from django.db.models import Q
from rest_framework import serializers

from core.api_common import OrgScopedViewSet
from apps.structure.models import Capability, OrgUnit, Role


class CapabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Capability
        fields = ["uuid", "key", "name", "description"]


class OrgUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgUnit
        fields = ["uuid", "name", "kind", "parent", "order"]


class RoleSerializer(serializers.ModelSerializer):
    unit_name = serializers.CharField(source="unit.name", read_only=True, default="")
    capability_keys = serializers.SlugRelatedField(
        source="capabilities", slug_field="key", many=True, read_only=True
    )

    class Meta:
        model = Role
        fields = [
            "id", "uuid", "key", "name", "description", "unit", "unit_name",
            "capability_keys", "is_seed",
        ]


class CapabilityViewSet(OrgScopedViewSet):
    queryset = Capability.objects.all()
    serializer_class = CapabilitySerializer


class OrgUnitViewSet(OrgScopedViewSet):
    queryset = OrgUnit.objects.all()
    serializer_class = OrgUnitSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get("search", "").strip()
        return queryset.filter(name__icontains=search) if search else queryset


class RoleViewSet(OrgScopedViewSet):
    queryset = Role.objects.select_related("unit").prefetch_related("capabilities").all()
    serializer_class = RoleSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get("search", "").strip()
        unit = self.request.query_params.get("unit", "").strip()
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
        if unit:
            queryset = queryset.filter(unit__uuid=unit)
        return queryset.order_by("name")
