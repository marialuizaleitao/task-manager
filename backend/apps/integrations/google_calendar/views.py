from django.conf import settings
from django.shortcuts import redirect
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.integrations.exceptions import AuthenticationExpiredError, ExternalServiceError

from . import oauth
from .models import GoogleCalendarCredential
from .serializers import GoogleCalendarStatusSerializer, GoogleCalendarToggleSerializer


class GoogleCalendarConnectView(APIView):
    """Devolve a URL de autorização do Google para o frontend redirecionar o usuário."""

    def get(self, request):
        url = oauth.build_authorization_url(request.user.id)
        return Response({"authorization_url": url})


class GoogleCalendarCallbackView(APIView):
    """Recebe o redirect do navegador após o consentimento no Google.

    É acessado diretamente pelo navegador (não por um fetch do frontend),
    por isso não exige JWT — o usuário é identificado pelo `state` assinado
    devolvido pelo próprio Google.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        if request.query_params.get("error"):
            return redirect(f"{settings.FRONTEND_BASE_URL}/tasks?google_calendar=error")

        code = request.query_params.get("code")
        state = request.query_params.get("state")
        if not code or not state:
            return redirect(f"{settings.FRONTEND_BASE_URL}/tasks?google_calendar=error")

        try:
            user_id = oauth.resolve_user_id_from_state(state)
            tokens = oauth.exchange_code_for_tokens(code)
        except (AuthenticationExpiredError, ExternalServiceError):
            return redirect(f"{settings.FRONTEND_BASE_URL}/tasks?google_calendar=error")

        GoogleCalendarCredential.objects.update_or_create(
            owner_id=user_id,
            defaults={
                "access_token": tokens.access_token,
                "refresh_token": tokens.refresh_token,
                "expires_at": tokens.expires_at,
                "enabled": True,
            },
        )
        return redirect(f"{settings.FRONTEND_BASE_URL}/tasks?google_calendar=connected")


class GoogleCalendarStatusView(APIView):
    def get(self, request):
        credential = GoogleCalendarCredential.objects.filter(owner=request.user).first()
        if credential is None:
            return Response({"connected": False, "enabled": False})

        serializer = GoogleCalendarStatusSerializer(credential)
        return Response({"connected": True, **serializer.data})


class GoogleCalendarToggleView(APIView):
    def post(self, request):
        credential = GoogleCalendarCredential.objects.filter(owner=request.user).first()
        if credential is None:
            return Response({"detail": "Google Calendar não está conectado."}, status=status.HTTP_404_NOT_FOUND)

        serializer = GoogleCalendarToggleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        credential.enabled = serializer.validated_data["enabled"]
        credential.save(update_fields=["enabled", "updated_at"])
        return Response({"connected": True, "enabled": credential.enabled})


class GoogleCalendarDisconnectView(APIView):
    def delete(self, request):
        credential = GoogleCalendarCredential.objects.filter(owner=request.user).first()
        if credential is None:
            return Response(status=status.HTTP_204_NO_CONTENT)

        # Revogação é best-effort: mesmo se o Google não responder, a
        # credencial local é removida e o token perde utilidade para nós.
        oauth.revoke_token(credential.refresh_token)
        credential.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
