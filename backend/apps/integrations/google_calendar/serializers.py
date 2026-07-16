from rest_framework import serializers

from .models import GoogleCalendarCredential


class GoogleCalendarStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoogleCalendarCredential
        fields = ["enabled", "calendar_id", "updated_at"]


class GoogleCalendarToggleSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
