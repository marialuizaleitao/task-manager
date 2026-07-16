from django.urls import path

from .views import (
    TelegramConfirmView,
    TelegramConnectView,
    TelegramDisconnectView,
    TelegramStatusView,
    TelegramToggleView,
)

app_name = "telegram"

urlpatterns = [
    path("telegram/connect/", TelegramConnectView.as_view(), name="connect"),
    path("telegram/confirm/", TelegramConfirmView.as_view(), name="confirm"),
    path("telegram/status/", TelegramStatusView.as_view(), name="status"),
    path("telegram/toggle/", TelegramToggleView.as_view(), name="toggle"),
    path("telegram/disconnect/", TelegramDisconnectView.as_view(), name="disconnect"),
]
