from rest_framework import serializers

from .models import TelegramConnection


class TelegramStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramConnection
        fields = ["telegram_username", "enabled", "last_contact_at"]


class TelegramToggleSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
