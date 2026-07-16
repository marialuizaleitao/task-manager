from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.integrations.exceptions import (
    AuthenticationExpiredError,
    ExternalServiceError,
    ProviderNotConfiguredError,
)

from .models import TelegramConnection
from .serializers import TelegramStatusSerializer, TelegramToggleSerializer
from .service import TelegramService


class TelegramConnectView(APIView):
    """Gera o código de vinculação e o deep link para o usuário abrir o bot."""

    def get(self, request):
        try:
            data = TelegramService().start_linking(request.user)
        except ProviderNotConfiguredError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except (ExternalServiceError, AuthenticationExpiredError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(data)


class TelegramConfirmView(APIView):
    """Verifica, sob demanda, se o usuário já enviou /start ao bot.

    Substitui o "callback/" do Google Calendar: não existe redirect de
    navegador no fluxo do Telegram, então a confirmação é um POST comum,
    disparado pelo usuário ao clicar em "Verificar conexão" no frontend.
    """

    def post(self, request):
        try:
            connection = TelegramService().confirm_linking(request.user)
        except ProviderNotConfiguredError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except (ExternalServiceError, AuthenticationExpiredError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        if not connection.is_linked():
            return Response(
                {"connected": False, "detail": "Ainda não recebemos sua mensagem no Telegram."}
            )

        serializer = TelegramStatusSerializer(connection)
        return Response({"connected": True, **serializer.data})


class TelegramStatusView(APIView):
    def get(self, request):
        connection = TelegramConnection.objects.filter(owner=request.user).first()
        if connection is None or not connection.is_linked():
            return Response({"connected": False, "enabled": False})

        serializer = TelegramStatusSerializer(connection)
        return Response({"connected": True, **serializer.data})


class TelegramToggleView(APIView):
    def post(self, request):
        serializer = TelegramToggleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            connection = TelegramService().set_enabled(request.user, serializer.validated_data["enabled"])
        except ProviderNotConfiguredError:
            return Response({"detail": "Telegram não está conectado."}, status=status.HTTP_404_NOT_FOUND)

        return Response({"connected": True, "enabled": connection.enabled})


class TelegramDisconnectView(APIView):
    def delete(self, request):
        TelegramService().disconnect(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
