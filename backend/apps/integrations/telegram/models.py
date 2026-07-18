from django.conf import settings
from django.db import models


class TelegramConnection(models.Model):
    """Vínculo entre um usuário e um chat do Telegram.

    Um usuário tem no máximo uma conexão (OneToOne): reconectar sobrescreve
    a anterior, assim como GoogleCalendarCredential.

    telegram_chat_id fica em branco enquanto a vinculação está pendente — o
    usuário gerou um linking_code mas ainda não confirmou (não enviou
    /start no bot). Ver TelegramService para o fluxo completo.

    telegram_chat_id NÃO é criptografado, ao contrário dos tokens OAuth do
    Google Calendar: ele não é uma credencial. Um chat_id sozinho não dá a
    quem o possui nenhum acesso — só o TELEGRAM_BOT_TOKEN (variável de
    ambiente, nunca no banco) permite enviar mensagens através dele. Ele é
    conceitualmente mais próximo de um identificador de contato do que de
    um segredo, então um CharField comum é suficiente (ver README,
    "Segurança").
    """

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="telegram_connection",
    )
    telegram_chat_id = models.CharField(max_length=64, blank=True)
    telegram_username = models.CharField(max_length=255, blank=True)
    linking_code = models.CharField(max_length=32, unique=True, null=True, blank=True)
    enabled = models.BooleanField(default=True)
    last_contact_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_linked(self) -> bool:
        return bool(self.telegram_chat_id)

    def __str__(self) -> str:
        return f"Telegram de {self.owner_id}"
