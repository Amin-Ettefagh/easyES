"""Accounts API: JWT login and the current-user endpoint.

Login issues a SimpleJWT access/refresh pair *and* returns a compact user
profile with the organizations the user can see, so the frontend can render the
shell in a single round-trip after sign-in. The demo user (amin/123456) is a
normal user row here — the password is hashed by Django, never stored plain
(see SECURITY.md).
"""
from __future__ import annotations

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    organizations = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "display_name", "email", "is_demo",
            "is_staff", "organizations",
        ]

    def get_organizations(self, obj):
        if obj.is_superuser:
            from apps.organizations.models import Organization

            qs = Organization.objects.all()
            return [{"uuid": str(o.uuid), "name": o.name, "slug": o.slug, "level": "admin"} for o in qs]
        out = []
        for m in obj.memberships.select_related("organization").all():
            out.append({
                "uuid": str(m.organization.uuid),
                "name": m.organization.name,
                "slug": m.organization.slug,
                "level": m.level,
            })
        return out


def _tokens_for(user) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    """Body: ``{"username": "amin", "password": "123456"}``.

    Returns ``{access, refresh, user}``. Deliberately generic on failure so we
    don't leak which usernames exist.
    """
    from django.contrib.auth import authenticate

    username = (request.data.get("username") or "").strip()
    password = request.data.get("password") or ""
    if not username or not password:
        return Response(
            {"detail": "username and password are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(request, username=username, password=password)
    if user is None or not user.is_active:
        return Response(
            {"detail": "invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
        )

    data = _tokens_for(user)
    data["user"] = UserSerializer(user, context={"request": request}).data
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    """The authenticated user's profile + visible organizations."""
    return Response(UserSerializer(request.user, context={"request": request}).data)
