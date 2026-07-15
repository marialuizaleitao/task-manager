from django.urls import path

from .views import (
    GoogleCalendarCallbackView,
    GoogleCalendarConnectView,
    GoogleCalendarDisconnectView,
    GoogleCalendarStatusView,
    GoogleCalendarToggleView,
)

app_name = "google_calendar"

urlpatterns = [
    path("google-calendar/connect/", GoogleCalendarConnectView.as_view(), name="connect"),
    path("google-calendar/callback/", GoogleCalendarCallbackView.as_view(), name="callback"),
    path("google-calendar/status/", GoogleCalendarStatusView.as_view(), name="status"),
    path("google-calendar/toggle/", GoogleCalendarToggleView.as_view(), name="toggle"),
    path("google-calendar/disconnect/", GoogleCalendarDisconnectView.as_view(), name="disconnect"),
]
