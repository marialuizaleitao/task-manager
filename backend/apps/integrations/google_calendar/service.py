"""Implementação de CalendarEventProvider (apps.integrations.interfaces) para o Google.

Único ponto que orquestra credenciais, refresh de token, o cliente HTTP e o
bookkeeping do vínculo tarefa/evento (GoogleCalendarEventLink). Registrado no
registry por GoogleCalendarConfig.ready() — apps.integrations.sync chama
estes métodos apenas através da interface, nunca importando esta classe
diretamente.
"""
from __future__ import annotations

from typing import Callable

from django.utils import timezone

from apps.integrations import notifications
from apps.integrations.exceptions import (
    AuthenticationExpiredError,
    ExternalServiceError,
    ProviderNotConfiguredError,
)
from apps.integrations.interfaces import NotificationEvent
from apps.tasks.models import Task

from . import oauth
from .client import GoogleCalendarClient
from .models import GoogleCalendarCredential, GoogleCalendarEventLink, SyncStatus


class GoogleCalendarService:
    def is_connected(self, user) -> bool:
        credential = self._get_credential(user)
        return credential is not None and credential.enabled

    def sync_create(self, task: Task) -> None:
        if task.due_date is None:
            return
        link, _ = GoogleCalendarEventLink.objects.get_or_create(task=task)
        self._call(task, link, lambda client: client.create_event(task))

    def sync_update(self, task: Task) -> None:
        link = GoogleCalendarEventLink.objects.filter(task=task).first()

        if task.due_date is None:
            # A tarefa deixou de ter due_date: se havia um evento, remove-o.
            if link is not None and link.google_event_id:
                self._call(task, link, lambda client: client.delete_event(link.google_event_id), is_delete=True)
            return

        if link is None or not link.google_event_id:
            # Nunca sincronizou (ou a última tentativa de criação falhou):
            # trata como uma criação em vez de PATCH em um evento inexistente.
            self.sync_create(task)
            return

        self._call(task, link, lambda client: client.update_event(task, link.google_event_id))

    def sync_delete(self, task: Task) -> None:
        link = GoogleCalendarEventLink.objects.filter(task=task).first()
        if link is None or not link.google_event_id:
            return
        self._call(task, link, lambda client: client.delete_event(link.google_event_id), is_delete=True)

    # -- internos -----------------------------------------------------------

    def _call(self, task: Task, link: GoogleCalendarEventLink, operation: Callable, *, is_delete: bool = False):
        try:
            credential = self._require_credential(task.owner)
            access_token = self._ensure_valid_token(credential)
            with GoogleCalendarClient(access_token, credential.calendar_id) as client:
                result = operation(client)
        except (AuthenticationExpiredError, ExternalServiceError, ProviderNotConfiguredError) as exc:
            self._mark_failed(link, exc)
            # Exclusão não gera aviso: a tarefa está prestes a ser removida
            # do Task Manager de qualquer forma (ver perform_destroy em
            # apps/tasks/views.py), então "sua tarefa continua salva
            # normalmente" não se aplicaria a este caso.
            if not is_delete:
                self._notify_sync_result(task, succeeded=False)
            raise

        if is_delete:
            link.delete()
        else:
            self._mark_synced(link, result)
            self._notify_sync_result(task, succeeded=True)
        return result

    def _notify_sync_result(self, task: Task, *, succeeded: bool) -> None:
        # Notificação best-effort de verdade: notifications.notify() nunca
        # lança exceção, então esta chamada nunca pode transformar um evento
        # de calendário (sucesso ou falha) em uma falha adicional aqui.
        key = "calendar.sync_succeeded" if succeeded else "calendar.sync_failed"
        notifications.notify(NotificationEvent(key=key, user=task.owner, subject=task))

    def _get_credential(self, user) -> GoogleCalendarCredential | None:
        return GoogleCalendarCredential.objects.filter(owner=user).first()

    def _require_credential(self, user) -> GoogleCalendarCredential:
        credential = self._get_credential(user)
        if credential is None or not credential.enabled:
            raise ProviderNotConfiguredError("Usuário não conectou o Google Calendar.")
        return credential

    def _ensure_valid_token(self, credential: GoogleCalendarCredential) -> str:
        if not credential.is_token_expired():
            return credential.access_token

        token = oauth.refresh_access_token(credential.refresh_token)
        credential.access_token = token.access_token
        credential.refresh_token = token.refresh_token
        credential.expires_at = token.expires_at
        credential.save(update_fields=["access_token", "refresh_token", "expires_at", "updated_at"])
        return credential.access_token

    def _mark_synced(self, link: GoogleCalendarEventLink, event_id: str) -> None:
        link.status = SyncStatus.SYNCED
        link.last_error = ""
        link.last_synced_at = timezone.now()
        if event_id:
            link.google_event_id = event_id
        link.save(update_fields=["status", "last_error", "last_synced_at", "google_event_id"])

    def _mark_failed(self, link: GoogleCalendarEventLink, exc: Exception) -> None:
        link.status = SyncStatus.FAILED
        link.last_error = str(exc)
        link.last_synced_at = timezone.now()
        link.save(update_fields=["status", "last_error", "last_synced_at"])
