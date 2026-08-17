"""Communications API: conversations between actors and their messages.

Read-only: messages are produced by the engine as agents talk, not by the UI.
"""
from __future__ import annotations

from rest_framework import serializers

from core.api_common import ReadOnlyOrgScopedViewSet
from apps.communications.models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender_actor.name", read_only=True, default="")
    node_key = serializers.CharField(source="node_run.node_key", read_only=True, default="")

    class Meta:
        model = Message
        fields = [
            "uuid", "role", "sender_name", "node_key", "content",
            "metadata", "created_at",
        ]


class ConversationSerializer(serializers.ModelSerializer):
    project_key = serializers.CharField(source="project.key", read_only=True, default="")
    message_count = serializers.IntegerField(source="messages.count", read_only=True)

    class Meta:
        model = Conversation
        fields = [
            "uuid", "kind", "topic", "project", "project_key", "execution",
            "message_count", "created_at",
        ]


class ConversationDetailSerializer(ConversationSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ["messages"]


class ConversationViewSet(ReadOnlyOrgScopedViewSet):
    queryset = Conversation.objects.select_related("project").all()
    serializer_class = ConversationSerializer

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ConversationDetailSerializer
        return ConversationSerializer
