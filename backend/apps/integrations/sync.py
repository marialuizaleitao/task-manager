"""Ponto único de sincronização de tarefas com provedores de calendário externos.

apps/tasks nunca importa google_calendar (ou qualquer outro provedor)
diretamente — chama apenas sync_task(task, action), que localiza os
provedores conectados via registry e delega a cada um.

A sincronização é best-effort: TaskViewSet já persistiu a tarefa antes de
chamar sync_task, então nenhuma falha aqui pode se propagar para o
cliente da API. Cada provedor registra seu próprio status/last_error;
esta função apenas garante isolamento entre provedores e loga o que
aconteceu, sem nunca lançar exceção.
"""
import logging

from .registry import get_calendar_provider, registered_calendar_providers

logger = logging.getLogger(__name__)

CREATE = "create"
UPDATE = "update"
DELETE = "delete"


def sync_task(task, action: str) -> None:
    for provider_key in registered_calendar_providers():
        provider = get_calendar_provider(provider_key)
        try:
            if not provider.is_connected(task.owner):
                continue

            if action == CREATE:
                provider.sync_create(task)
            elif action == UPDATE:
                provider.sync_update(task)
            elif action == DELETE:
                provider.sync_delete(task)
            else:
                raise ValueError(f"Ação de sincronização desconhecida: {action!r}")
        except Exception:
            # Best-effort por design: uma falha de sincronização nunca pode
            # comprometer a resposta da API de tarefas. O provedor já
            # registrou o próprio status/last_error antes de propagar aqui;
            # este log serve à observabilidade, não ao usuário.
            logger.exception(
                "Falha ao sincronizar tarefa %s com o provedor %s (ação=%s)",
                task.id,
                provider_key,
                action,
            )
