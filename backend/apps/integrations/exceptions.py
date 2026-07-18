"""Exceções compartilhadas por qualquer integração com serviço externo.

Vivem aqui (e não dentro de google_calendar) porque todo provedor futuro
(Outlook, Slack, Notion) vai lidar com os mesmos três cenários: falha de
rede/HTTP, credencial expirada/revogada e provedor não configurado para o
usuário. Um único vocabulário de erros permite que apps/tasks.sync trate
qualquer provedor de forma genérica.
"""


class IntegrationError(Exception):
    """Erro base para qualquer falha relacionada a uma integração externa."""


class ProviderNotConfiguredError(IntegrationError):
    """O usuário não conectou este provedor, ou a sincronização está desabilitada."""


class AuthenticationExpiredError(IntegrationError):
    """As credenciais foram rejeitadas e uma nova autorização é necessária.

    Cobre tanto um refresh_token inválido/revogado (invalid_grant) quanto um
    access_token rejeitado (401) sem possibilidade de renovação automática.
    """


class ExternalServiceError(IntegrationError):
    """A chamada ao serviço externo falhou (timeout, rede ou status de erro)."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
