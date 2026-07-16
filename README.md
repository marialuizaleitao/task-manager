# Task Manager

Aplicação web de gerenciamento de tarefas (To-Do List), desenvolvida como case técnico para demonstrar práticas profissionais de engenharia de software: arquitetura em camadas, containerização, testes automatizados e CI/CD.

> **Status atual:** Sprint 7 concluída — autenticação (JWT), categorias, CRUD de tarefas, compartilhamento, busca/filtros/ordenação avançados, integração com o Google Calendar e notificações via Telegram Bot API funcionais no backend e no frontend.

## Tecnologias

**Backend**
- Python 3.13
- Django 5.2 (LTS) + Django REST Framework 3.17
- djangorestframework-simplejwt (autenticação JWT)
- django-filter (filtros combináveis via FilterSet)
- httpx (cliente HTTP para integrações externas)
- cryptography / Fernet (criptografia de credenciais OAuth em repouso)
- PostgreSQL 18
- django-environ (configuração via variáveis de ambiente)
- pytest + pytest-django

**Frontend**
- React 19 + TypeScript
- React Router
- Vite 8

**Infraestrutura**
- Docker + Docker Compose
- Nginx (servindo o build de produção do frontend)

## Arquitetura

O backend segue separação em camadas:

```
Views → Services → Repositories (quando houver ganho real) → Models
```

Regras de negócio ficam concentradas em services quando há lógica real a isolar (ex.: `accounts.services.register_user`). Módulos com CRUD simples e sem orquestração adicional (`categories`, `tasks`) resolvem tudo em serializer + viewset, sem um service artificial. Repositories são introduzidos apenas quando reduzem acoplamento de forma concreta — ainda não há necessidade real no projeto.

O frontend é organizado por responsabilidade (componentes, páginas, hooks, contextos e serviços de API), seguindo o mesmo princípio: cada pasta só existe quando há conteúdo real que a justifique. Tipos genéricos reutilizados por mais de um serviço (ex.: resposta paginada) ficam em um módulo próprio (`services/pagination.ts`) em vez de duplicados.

### Autorização e compartilhamento de tarefas

Desde a Sprint 4, o projeto tem dois mecanismos de autorização que atuam em conjunto:

- **`get_queryset()`** continua decidindo o que é *visível*: na listagem principal (`GET /api/tasks/`), só tarefas do próprio usuário; nas ações de detalhe, tarefas próprias e tarefas compartilhadas.
- **`TaskAccessPermission`** (`apps/sharing/permissions.py`) decide o que é *permitido* dentro do que é visível, por ação: o dono tem acesso irrestrito; um compartilhamento `READ` permite apenas visualizar; um compartilhamento `EDIT` permite visualizar e editar, mas nunca excluir a tarefa nem gerenciar seus compartilhamentos.

O modelo de compartilhamento (`TaskShare`) é uma tabela intermediária simples — `task`, `shared_with`, `permission`, `created_at`, com uma constraint de unicidade por par tarefa/usuário — em vez de um `ManyToManyField` com `through` (que adicionaria uma camada de açúcar sintático sem uso real, já que toda consulta relevante precisa do `permission` junto do usuário) ou de uma ACL genérica via `contenttypes` (abstração prematura: hoje só `Task` precisa ser compartilhável).

`apps/sharing` existe como app própria porque compartilhamento é uma responsabilidade distinta de CRUD de tarefa — mesmo com as rotas de gerenciamento de compartilhamento aninhadas em `/api/tasks/{id}/...` por serem parte do recurso `Task`, todo o modelo, serializers e a permission class vivem em `sharing`.

### Busca, filtros e ordenação de tarefas

A partir da Sprint 5, `TaskViewSet` e `SharedTaskListView` (`/api/shared-tasks/`) compartilham o mesmo pipeline de filtragem, definido uma única vez em `apps/tasks/filters.py`:

- **`TaskFilterSet`** (django-filter) resolve os filtros combináveis: `category` (aceitando o sentinel `none`), `completed`, `due_date_before/after`, `created_before/after`. Um `FilterSet` declarativo passou a valer a pena aqui porque são 6 filtros combináveis — abaixo disso (como o filtro único de nome em `categories`, Sprint 2) um `if` simples continua sendo a escolha certa.
- **`SearchFilter`** (`search_fields = ["title", "description"]`) cobre a busca textual — `icontains` já é nativamente case insensitive.
- **`OrderingFilter`** (`ordering_fields = ["title", "due_date", "created_at", "updated_at"]`) permite ordenação apenas pelos campos explicitamente liberados; qualquer outro campo em `?ordering=` é ignorado silenciosamente pelo próprio DRF, sem erro e sem expor colunas não previstas.

Não existe filtro `?shared=true` em `/api/tasks/`: a listagem principal permanece restrita ao próprio dono (regra da Sprint 4), e `/api/shared-tasks/` já cobre "tarefas compartilhadas comigo" — reaproveitando o mesmo `FilterSet`/busca/ordenação em vez de duplicar essa lógica ou misturar as duas listagens.

Dois índices compostos (`Task.Meta.indexes`) foram adicionados nesta sprint — `(owner, due_date)` e `(owner, -created_at)` — depois de confirmar via `QuerySet.explain()` que filtrar ou ordenar por esses campos forçava um `TEMP B-TREE` mesmo após a redução por `owner_id` via índice. Nenhum outro índice foi criado: filtro por `completed` (baixa cardinalidade) e por `category` (já indexado pela FK) não mostraram esse padrão.

### Módulo de integrações e sincronização com o Google Calendar

A partir da Sprint 6, o projeto ganhou um módulo de integrações desenhado para múltiplos provedores externos, não apenas para o Google. `apps/integrations` concentra o que é comum a qualquer provedor:

- **`interfaces.py`** define `CalendarEventProvider` (`typing.Protocol`) com `is_connected`, `sync_create`, `sync_update` e `sync_delete`. `apps/tasks` depende apenas deste contrato.
- **`registry.py`** é um dicionário simples de provedores registrados por chave (`"google_calendar"` → `GoogleCalendarService`). Cada provedor se registra sozinho, no `ready()` do próprio `AppConfig`.
- **`sync.py`** expõe a única função que `apps/tasks` conhece: `sync_task(task, action)`. Ela percorre os provedores conectados via `registry` e delega a cada um — `apps/tasks` nunca importa `google_calendar` diretamente.
- **`exceptions.py`** define o vocabulário de erro compartilhado (`ExternalServiceError`, `AuthenticationExpiredError`, `ProviderNotConfiguredError`), para que `sync.py` trate qualquer provedor de forma genérica.
- **`crypto.py`** implementa `EncryptedTextField` (Fernet), reutilizável por qualquer credencial de integração futura.

Cada provedor concreto vive em sua própria app Django aninhada, com models e migrations independentes — `apps.integrations.google_calendar` é a primeira. Um futuro provedor (Outlook Calendar, Google Tasks) seguiria a mesma estrutura (`apps.integrations.outlook_calendar`, por exemplo), sem tocar em `apps/tasks` nem nos demais provedores: só precisa implementar `CalendarEventProvider` e se registrar.

**Por que uma app Django por provedor, e não uma única app `integrations` com todos os models juntos:** cada provedor tem seu próprio ciclo de vida de schema. Se `GoogleCalendarCredential` e um futuro `OutlookCredential` dividissem o mesmo histórico de migrations, remover ou substituir um provedor exigiria mexer no histórico do outro. Apps aninhadas com migrations próprias tornam cada integração genuinamente independente.

**Fluxo OAuth2 (Authorization Code / "Web Server Flow"):** o usuário é redirecionado para `accounts.google.com`, autoriza o escopo `calendar.events` (não o acesso completo à agenda — princípio do menor privilégio) e o Google devolve um `code` para `GET /callback/`. Como esse redirect é uma navegação de navegador comum, sem `Authorization: Bearer`, o usuário é identificado por um `state` assinado (`django.core.signing`, expira em 10 minutos) em vez de JWT. O backend troca o `code` por `access_token` + `refresh_token` em `oauth2.googleapis.com/token`, usando `access_type=offline` e `prompt=consent` para garantir que o `refresh_token` seja sempre emitido. Um `access_token` expirado é renovado automaticamente antes de cada chamada (`GoogleCalendarService._ensure_valid_token`); se o Google responder `invalid_grant`, isso é tratado como necessidade de nova autorização — nunca como erro fatal.

**Cliente HTTP — `httpx` próprio em vez do SDK oficial do Google:** o projeto já usa `httpx` como padrão de cliente HTTP (decisão herdada de sprints anteriores: timeouts de primeira classe, tipagem, `HTTPTransport` com retry declarativo). O SDK oficial (`google-api-python-client`) resolve endpoints via *discovery* dinâmico em runtime, o que tornaria o fluxo OAuth2 menos explícito e adicionaria uma segunda forma de fazer HTTP no projeto. Um cliente próprio (`google_calendar/client.py` e `oauth.py`), consumindo a REST API v3 diretamente, mantém consistência arquitetural e reaproveita o mesmo tratamento de erro das demais camadas.

**Síncrono, não assíncrono:** o restante do backend (Django + DRF clássico, sem ASGI) é inteiramente síncrono; introduzir chamadas assíncronas apenas nesta integração exigiria uma ponte `async`/`sync` sem nenhum ganho real, já que a sincronização acontece dentro do ciclo request/response de uma única operação de tarefa.

**Sincronização best-effort, nunca bloqueante:** `TaskViewSet.perform_create/perform_update/perform_destroy` chamam `sync_task` depois que a tarefa já foi persistida no banco. Qualquer falha do Google (timeout, 401, 5xx, indisponibilidade) é capturada dentro do próprio provedor — que registra `status` (`pending`/`synced`/`failed`), `last_error` e `last_synced_at` em `GoogleCalendarEventLink` — e por `sync.py`, que nunca deixa uma exceção escapar para a view. A criação, edição ou remoção de uma tarefa **nunca** falha por causa do Google estar fora do ar. Sem uma fila (Celery está fora do escopo desta sprint), não há retry automático em segundo plano — uma falha só é corrigida na próxima operação sobre a mesma tarefa (`sync_update` detecta um vínculo sem `google_event_id` e tenta criar novamente).

**Eventos de dia inteiro:** só tarefas com `due_date` sincronizam. O Google trata o fim de eventos de dia inteiro como exclusivo, então `due_date` vira `start.date = due_date` e `end.date = due_date + 1 dia`.

**Seam para cache futuro, sem Redis nesta sprint:** o ponto de extensão é `GoogleCalendarService` — por exemplo, cachear se um `google_event_id` já existe antes de decidir entre criar (`POST`) ou atualizar (`PATCH`). Nenhuma mudança na interface `CalendarEventProvider` seria necessária; `apps/tasks` e `sync.py` não saberiam que o cache existe.

**Retries e timeout:** `GoogleCalendarClient` usa `httpx.HTTPTransport(retries=GOOGLE_API_MAX_RETRIES)`, que cobre falhas de conexão (DNS, timeout de conexão) — não substitui o backoff exponencial documentado pelo Google para respostas `429`/`5xx` de quota, que exigiria uma fila para ser feito com segurança fora do ciclo request/response e fica registrado como débito técnico. O timeout (`GOOGLE_API_TIMEOUT_SECONDS`, padrão 10s) limita o pior caso de latência adicionada à criação/edição de uma tarefa.

### Notificações via Telegram Bot API

A partir da Sprint 7, o módulo de integrações ganhou um segundo tipo de provedor, independente do calendário: notificações de tarefas. A extensão reaproveita a arquitetura da Sprint 6 em vez de duplicá-la:

- **`interfaces.py`** ganhou `TaskNotificationProvider` (`typing.Protocol`), irmão de `CalendarEventProvider`: `is_connected`, `notify_task_created`, `notify_task_completed`, `notify_task_overdue`.
- **`registry.py`** ganhou um segundo dicionário, `_notification_providers`, com as mesmas funções (`register_notification_provider`, `get_notification_provider`, `registered_notification_providers`) espelhando o registry de calendário. Dois dicionários simples, em vez de um registry genérico parametrizado por "tipo de provedor": com apenas duas famílias de provedor, a generalização adicionaria indireção sem reduzir código real.
- **`sync.py`** ganhou `notify_task(task, event)`, irmã de `sync_task(task, action)`, com `TaskEvent.CREATED/COMPLETED/OVERDUE`. Mesmo contrato best-effort: percorre os provedores conectados e isola a falha de cada um em `try/except Exception: logger.exception(...)`, sem nunca propagar para quem chamou.

`apps.integrations.telegram` é uma app aninhada nos mesmos moldes de `google_calendar` — model e migration próprios, registrada no `registry` pelo `ready()` do seu `AppConfig`.

**Modelagem — `TelegramConnection`:** `owner` (`OneToOneField`), `telegram_chat_id`, `telegram_username`, `enabled`, `last_contact_at`, `created_at`, `updated_at`, como sugerido, mais um campo adicional: **`linking_code`** (`CharField`, único, nulo enquanto não há vinculação pendente). Ele existe porque o fluxo de vinculação (ver abaixo) precisa de um identificador de uso único para uma vinculação em andamento, e nenhum dos campos sugeridos cobre essa responsabilidade sem sobrecarregar seu propósito original.

**Segurança — por que `telegram_chat_id` não é criptografado:** ao contrário dos tokens OAuth do Google Calendar (`EncryptedTextField`/Fernet), um `chat_id` sozinho não concede acesso a nada — só o `TELEGRAM_BOT_TOKEN` (variável de ambiente, nunca persistido no banco) permite enviar mensagens através dele. Um `chat_id` vazado permitiria, no máximo, que outra aplicação identificasse o mesmo chat *se também possuísse* um bot token válido — o que já pressupõe comprometimento de um segredo mais sensível. Ele é conceitualmente um identificador de contato, não uma credencial, por isso um `CharField` comum é suficiente.

**Vinculação via deep link + código de uso único, não "informe seu @username":** a Bot API não permite que um bot inicie contato com um usuário nem resolva um `chat_id` a partir de um `@username` — só é possível responder depois que o próprio usuário envia a primeira mensagem (proteção da própria API contra spam). O fluxo, então, é: `TelegramService.start_linking(user)` gera um `linking_code` e monta `https://t.me/<bot_username>?start=<code>` (usando `client.get_me()` para obter o username do bot); o usuário abre o link e envia `/start <code>`; `TelegramService.confirm_linking(user)` busca atualizações recentes via `client.get_updates()`, localiza a mensagem com esse texto exato e extrai `chat_id`/`username` dela.

**`getUpdates` com `timeout=0`, sem long polling:** `confirm_linking` é chamado de forma síncrona dentro do ciclo request/response de `POST /telegram/confirm/`, disparado pelo clique em "Verificar conexão" no frontend — nunca por um worker em segundo plano. Um long poll do Telegram (que pode aguardar até ~50s por uma atualização) bloquearia a thread do servidor web pelo mesmo tempo, inaceitável nesse ciclo. Ver "Performance" abaixo para a comparação completa com webhook.

**Sem offset persistente entre chamadas a `getUpdates` (débito técnico aceito):** cada chamada busca as atualizações recentes (a Bot API mantém as últimas ~100 ou ~24h) e filtra pela mensagem com o `linking_code` exato, que é único por vinculação pendente — reprocessar atualizações antigas é seguro (idempotente), só um pouco menos eficiente do que confirmar um offset a cada chamada.

**Notificações são best-effort, nunca bloqueantes:** `TaskViewSet.perform_create/perform_update` chamam `notify_task` depois que a tarefa já foi persistida — o mesmo ponto de integração usado por `sync_task` (Google Calendar), sem que `apps/tasks` importe `telegram` em nenhum momento. Falha de envio (timeout, bot bloqueado, chat inexistente, rate limit) nunca impede a criação, edição ou exclusão de uma tarefa: é capturada dentro do próprio `notify_task` e apenas registrada em log.

**Chat inalcançável desabilita a conexão automaticamente:** se o Telegram responder que o bot foi bloqueado, o chat não existe mais, ou o usuário foi removido/desativado (`ChatUnreachableError`, `client.py`), `TelegramService.send_text` marca `enabled = False` e propaga o erro para ser registrado como falha best-effort — sem apagar `telegram_chat_id`/`telegram_username`, para que reconectar não exija repetir o fluxo de vinculação caso o usuário apenas desbloqueie o bot e reenvie `/start`.

**Notificação de tarefa criada respeita `due_date`:** assim como a sincronização com o Google Calendar, `notify_task_created` só envia mensagem se a tarefa tiver `due_date` — sem prazo, não há o que comunicar de imediato.

**Resumo diário e tarefa vencida — infraestrutura pronta, sem agendador:** `notify_task_overdue` e `DailySummaryService` (em `telegram/service.py` — não há responsabilidade distinta o bastante para justificar um arquivo próprio só para ele) estão implementados e testados nesta sprint, mas não são disparados automaticamente por nada: não há Celery, Redis, scheduler ou cron job neste momento (fora do escopo desta sprint, por decisão explícita). `DailySummaryService.build_message(user)` é uma função pura, testável sem mockar HTTP, e `send_summary(user)` apenas a envia via `TelegramService.send_text` — o ponto exato onde uma tarefa periódica futura do Celery Beat chamaria `send_summary` para cada usuário conectado, sem qualquer mudança nesta classe.

## Estrutura de diretórios

```
task-manager/
├── backend/
│   ├── apps/
│   │   ├── accounts/       # Custom User, JWT, registro, login, /me
│   │   ├── categories/     # CRUD de categorias
│   │   ├── tasks/          # CRUD de tarefas, filtros (filters.py)
│   │   ├── sharing/        # Compartilhamento de tarefas (TaskShare, permissions)
│   │   └── integrations/   # Módulo de integrações externas
│   │       ├── interfaces.py, registry.py, sync.py, exceptions.py, crypto.py
│   │       ├── google_calendar/   # App própria: models, oauth, client, service
│   │       └── telegram/          # App própria: models, client, service, views
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── dev.py
│   │   │   ├── prod.py
│   │   │   └── test.py
│   │   ├── urls.py
│   │   ├── views.py        # views de infraestrutura (health check)
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── requirements/
│   │   ├── base.txt
│   │   ├── dev.txt
│   │   └── prod.txt
│   ├── conftest.py
│   ├── pytest.ini
│   ├── manage.py
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/     # CategoryForm/List, TaskForm/List, TaskShareManager, GoogleCalendarPanel, TelegramPanel, ProtectedRoute
│   │   ├── contexts/       # AuthContext / AuthProvider
│   │   ├── hooks/
│   │   ├── pages/          # LoginPage, RegisterPage, HomePage, CategoriesPage, TasksPage, SharedTasksPage
│   │   ├── services/       # clientes de API (auth, categories, tasks, sharing, pagination, tokenStorage)
│   │   ├── App.tsx
│   │   └── main.tsx
│   └── Dockerfile
├── docker/
│   └── nginx/
│       └── nginx.conf
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
└── README.md
```

## Fluxo Git

```
master → develop → feature/*
```

Nenhum commit é feito diretamente em `master`. Funcionalidades são desenvolvidas em branches `feature/*`, `fix/*`, `refactor/*`, `docs/*` ou `test/*`, com Pull Request para `develop`. Merges de `develop` para `master` ocorrem apenas após um conjunto estável e testado de funcionalidades.

Commits seguem [Conventional Commits](https://www.conventionalcommits.org/).

## Variáveis de ambiente

Copie `.env.example` para `.env` antes de subir o projeto:

```bash
cp .env.example .env
```

| Variável | Descrição |
|---|---|
| `DJANGO_SETTINGS_MODULE` | Módulo de settings ativo (`config.settings.dev` ou `config.settings.prod`) |
| `DJANGO_SECRET_KEY` | Chave secreta do Django |
| `DJANGO_DEBUG` | Ativa/desativa modo debug |
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos, separados por vírgula |
| `CORS_ALLOWED_ORIGINS` | Origens permitidas para requisições CORS |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | Credenciais do banco |
| `POSTGRES_HOST` / `POSTGRES_PORT` | Endereço do banco |
| `VITE_API_URL` | URL base da API consumida pelo frontend |
| `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` | Credenciais do OAuth Client do Google Cloud |
| `GOOGLE_OAUTH_REDIRECT_URI` | URL de callback do backend, cadastrada no Google Cloud |
| `GOOGLE_TOKEN_ENCRYPTION_KEY` | Chave Fernet para cifrar tokens OAuth em repouso |
| `FRONTEND_BASE_URL` | URL do frontend para onde o navegador retorna após o fluxo OAuth |
| `TELEGRAM_BOT_TOKEN` | Token do bot Telegram, obtido com o @BotFather — nunca armazenado no banco |

Sem `GOOGLE_OAUTH_CLIENT_ID`/`GOOGLE_OAUTH_CLIENT_SECRET`/`GOOGLE_TOKEN_ENCRYPTION_KEY` configurados, o restante do sistema continua funcionando normalmente — apenas a integração com o Google Calendar fica indisponível.

Sem `TELEGRAM_BOT_TOKEN` configurado, o restante do sistema também continua funcionando normalmente — apenas a integração com o Telegram fica indisponível (`ProviderNotConfiguredError`, retornado como 503 pelos endpoints `telegram/*`).

## Execução com Docker

Pré-requisitos: Docker e Docker Compose instalados.

```bash
cp .env.example .env
docker compose up --build
docker compose exec backend python manage.py migrate
```

- Backend: http://localhost:8000/api/health/
- Frontend: http://localhost:5173

Para o ambiente de produção (build otimizado do frontend servido via Nginx, backend via Gunicorn):

```bash
docker compose -f docker-compose.prod.yml up --build
```

## Configurar o Google Cloud (integração com o Google Calendar)

1. Crie (ou reutilize) um projeto em [console.cloud.google.com](https://console.cloud.google.com).
2. Em **APIs e Serviços → Biblioteca**, ative a **Google Calendar API**.
3. Em **APIs e Serviços → Tela de consentimento OAuth**:
   - Tipo de usuário: **Externo**.
   - Publicação: mantenha em **Testing** (ver "Limitações conhecidas" abaixo).
   - Em **Test users**, adicione o e-mail Google de quem for validar a integração — sem isso, o Google recusa o consentimento.
4. Em **APIs e Serviços → Credenciais → Criar credenciais → ID do cliente OAuth**:
   - Tipo de aplicativo: **Aplicativo da Web**.
   - URI de redirecionamento autorizado: o mesmo valor de `GOOGLE_OAUTH_REDIRECT_URI` (por padrão, `http://localhost:8000/api/integrations/google-calendar/callback/`).
5. Copie o **ID do cliente** e o **Segredo do cliente** para `GOOGLE_OAUTH_CLIENT_ID` e `GOOGLE_OAUTH_CLIENT_SECRET` no `.env`.
6. Gere a chave de criptografia dos tokens:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
   e defina o resultado em `GOOGLE_TOKEN_ENCRYPTION_KEY`.

### Solução de problemas

Toda variável de ambiente da integração pode ser conferida em runtime, dentro do container:

```bash
docker compose exec backend python -c "from django.conf import settings; print(repr(settings.GOOGLE_TOKEN_ENCRYPTION_KEY))"
```

Isso resolve a maioria dos erros abaixo mais rápido do que ler o traceback.

- **O Compose só lê o `.env` ao criar o container, não a cada `restart`.** Depois de editar o `.env`, `docker compose restart backend` não é suficiente — o processo continua com as variáveis antigas. Use `docker compose up -d --force-recreate backend` (ou `down && up`).
- **`Missing required parameter: client_id` na tela do Google:** o backend está enviando `GOOGLE_OAUTH_CLIENT_ID` vazio. Quase sempre é o ponto anterior — o container não recriado depois que a variável foi adicionada ao `.env`.
- **`Fernet key must be 32 url-safe base64-encoded bytes`:** `GOOGLE_TOKEN_ENCRYPTION_KEY` está ausente, vazia ou corrompida. Confira com o comando acima; o valor precisa ter exatamente 44 caracteres (32 bytes em base64).
- **Mesmo erro, mas com `Incorrect padding` no traceback:** o valor da chave foi salvo com quebra de linha `CRLF` (comum em editores do Windows) ou está entre aspas. Nunca envolva valores em aspas no `.env` — `docker compose` não remove aspas, elas passam a fazer parte do valor.
- **Mesmo erro novamente, mesmo depois de corrigir:** confira se a linha no `.env` não ficou duplicada (ex.: `GOOGLE_TOKEN_ENCRYPTION_KEY=GOOGLE_TOKEN_ENCRYPTION_KEY=...`), o que acontece ao colar um valor por cima de uma correção anterior sem apagar o prefixo. Rode `grep GOOGLE_TOKEN_ENCRYPTION_KEY .env` e confirme que existe uma única linha, com um único `=`.

## Criar um Bot no Telegram (integração de notificações)

1. No Telegram, inicie uma conversa com **[@BotFather](https://t.me/BotFather)**.
2. Envie `/newbot` e siga as instruções: escolha um nome de exibição e um `username` terminado em `bot` (ex.: `task_manager_case_bot`).
3. O BotFather devolve o **token do bot** (formato `123456789:AAH...`). Copie-o para `TELEGRAM_BOT_TOKEN` no `.env` — nunca o compartilhe nem o versione.
4. Reconstrua o container do backend para que a nova variável seja lida (`docker compose up -d --force-recreate backend`, mesma ressalva da seção anterior).

### Como vincular sua conta

1. Na página de tarefas do frontend, na seção **Telegram**, clique em **Conectar Telegram**. Isso abre, em uma nova aba, o deep link `https://t.me/<bot>?start=<código>`.
2. No Telegram, envie a mensagem `/start <código>` que já vem preenchida ao abrir o link (basta clicar em **Iniciar**).
3. De volta ao frontend, clique em **Verificar conexão**. O backend consulta `getUpdates`, localiza sua mensagem e conclui a vinculação.

### Endpoints

Todos exigem autenticação JWT (`Authorization: Bearer <token>`), como o restante da API.

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/integrations/telegram/connect/` | Gera um novo `linking_code` e retorna o deep link do bot |
| `POST` | `/api/integrations/telegram/confirm/` | Verifica se o `/start <código>` já chegou e finaliza a vinculação |
| `GET` | `/api/integrations/telegram/status/` | Retorna `connected`, `telegram_username`, `enabled`, `last_contact_at` |
| `POST` | `/api/integrations/telegram/toggle/` | Habilita/desabilita notificações (`{"enabled": true/false}`) sem desvincular |
| `DELETE` | `/api/integrations/telegram/disconnect/` | Remove a vinculação — nenhuma mensagem é enviada depois disso |

### Exemplos de mensagem

Tarefa criada (só quando há `due_date`):

```
🆕 Nova tarefa

Título:
Enviar documentação

Prazo:
20/07/2026

Categoria:
Trabalho
```

Tarefa concluída:

```
✅ Tarefa concluída

Título:
Enviar documentação
```

Tarefa vencida (implementado e testado, sem disparo automático nesta sprint — ver "Limitações conhecidas"):

```
⚠️ Tarefa vencida

Título:
Enviar documentação

Prazo:
20/07/2026
```

## Performance

**Por que polling (`getUpdates`) em vez de webhook nesta sprint:** um webhook exigiria um endpoint HTTPS publicamente acessível, com certificado válido, para o qual o Telegram enviaria atualizações via `POST` — viável apenas após o deploy (Sprint 10). Em desenvolvimento local, sem um domínio público, o webhook exigiria um túnel adicional (ngrok ou similar) só para testar a vinculação. `getUpdates` com `timeout=0` funciona identicamente em qualquer ambiente, sem infraestrutura extra, ao custo de ser chamado sob demanda (a cada clique em "Verificar conexão") em vez de receber atualizações em tempo real — uma troca aceitável, já que a única atualização que o bot processa hoje é a confirmação de vinculação. Migrar para webhook no futuro não exigiria mudanças em `TelegramService`: apenas trocar como `TelegramClient` recebe as atualizações.

**Como o Celery entraria no futuro, sem mudar esta arquitetura:** `notify_task_overdue` e `DailySummaryService.send_summary` já existem e são testados; falta apenas *chamá-los* periodicamente. Uma tarefa periódica do Celery Beat (ex.: a cada hora, verificando tarefas com `due_date` no passado e `completed=False`) chamaria `sync.notify_task(task, TaskEvent.OVERDUE)` por tarefa vencida, e outra (diária, ex. 8h) chamaria `DailySummaryService().send_summary(user)` por usuário conectado. Nenhuma delas precisaria conhecer `TelegramService` diretamente — o mesmo desacoplamento via `registry`/`sync.py` que já existe hoje.

**Como o Redis entraria no futuro, sem mudar esta arquitetura:** Redis serviria a dois papéis independentes, ambos plugáveis sem alterar `CalendarEventProvider`/`TaskNotificationProvider`: (1) *broker* do Celery, para as tarefas periódicas acima; (2) cache de estado, por exemplo armazenar o `offset` de `getUpdates` entre chamadas (resolvendo o débito técnico descrito abaixo) ou um contador simples para rate limiting local (evitar estourar o limite de ~30 mensagens/segundo da Bot API antes mesmo de tentar enviar). Nenhum desses usos exige mudança na interface pública dos serviços — são detalhes de implementação interna de `TelegramService`/`TelegramClient`.

## Limitações conhecidas

- **Escopo `calendar.events` é sensível para o Google** e exigiria um processo de verificação do app para uso público (vídeo demonstrativo, política de privacidade hospedada, revisão manual). Para este projeto — um case técnico, não um produto com usuários reais — o app permanece deliberadamente em modo **Testing**: funciona normalmente para até 100 usuários adicionados manualmente como **Test users** na tela de consentimento OAuth, sem o custo do processo de verificação. Isso é uma decisão consciente, não uma falha.
- **Sem fila de tarefas em segundo plano (Celery está fora do escopo desta sprint)**: a sincronização com o Google Calendar é best-effort e síncrona. Uma falha de sincronização só é corrigida automaticamente na próxima operação sobre a mesma tarefa, não por um retry agendado.
- **Backoff de quota não implementado**: o cliente HTTP do Google Calendar tem retry de conexão e timeout configuráveis, mas não implementa o backoff exponencial documentado pelo Google para respostas `429`/`5xx` de limite de quota — o volume de uso de um projeto de demonstração não justifica essa complexidade agora, mas fica registrado como débito técnico caso o volume de sincronizações cresça.
- **Um único calendário por usuário** (`calendar_id`, padrão `"primary"`): não há UI para escolher entre múltiplos calendários da conta Google.
- **Polling em vez de webhook para o Telegram**: `getUpdates` é consultado sob demanda (ao clicar em "Verificar conexão"), não em tempo real. Ver "Performance" acima para a justificativa completa.
- **Sem offset persistente entre chamadas a `getUpdates`**: cada confirmação de vinculação reprocessa as atualizações recentes em vez de retomar de um ponto salvo — seguro (idempotente, filtrado por `linking_code` único), porém um pouco menos eficiente. Resolvido facilmente com Redis no futuro (ver "Performance").
- **Resumo diário e notificação de tarefa vencida não são disparados automaticamente**: `DailySummaryService` e `notify_task_overdue` estão implementados e testados, mas não há Celery Beat, cron ou qualquer scheduler nesta sprint — por decisão explícita de escopo. Ver "Performance" para como essa peça se encaixaria no futuro sem mudar a arquitetura atual.
- **Rate limit da Bot API não tratado de forma proativa**: o projeto não implementa throttling local para o limite de ~30 mensagens/segundo do Telegram — no volume de uso de uma demonstração, isso nunca é atingido, mas fica registrado como débito técnico caso o número de usuários conectados cresça.

## Testes

```bash
docker compose exec backend pytest -v
```

Nenhum teste chama o Google ou o Telegram de verdade. `apps.integrations.google_calendar.tests` cobre OAuth (troca de código, refresh, `invalid_grant`, timeout, erro HTTP, resposta inválida), o cliente da Calendar API (criação/atualização/exclusão de evento, 401, 5xx, timeout), o `service` (best-effort, refresh automático de token, transições ao adicionar/remover `due_date`) e as views (connect/callback/status/toggle/disconnect) — usando `monkeypatch` sobre `httpx.post`/`httpx.Client.request` com objetos `httpx.Response` reais, sem rede. `apps.integrations.telegram.tests` cobre o `TelegramClient` (`getMe`, `sendMessage`, `getUpdates`, 401, chat bloqueado/inexistente, timeout, erro de rede, JSON inválido), o `TelegramService` (conexão, notificações, vinculação, desconexão) e o `DailySummaryService`, com a mesma estratégia de `monkeypatch` sobre a classe `TelegramClient` — nenhuma chamada HTTP real. `apps.integrations.tests` cobre `crypto.py`, `registry.py` (incluindo os dois registries independentes) e `sync.py` (`sync_task` e `notify_task`) isoladamente, com provedores dublês (`MagicMock`). `apps/tasks/tests/test_google_calendar_sync.py` e `apps/tasks/tests/test_telegram_notifications.py` verificam que `TaskViewSet` aciona `sync_task`/`notify_task` nos pontos certos, sem testar os provedores em si.

## Roadmap

| Sprint | Escopo | Status |
|---|---|---|
| 0 | Estrutura inicial, Docker, configuração base | Concluído |
| 1 | Autenticação (JWT), cadastro e login | Concluído |
| 2 | Categorias | Concluído |
| 3 | CRUD de tarefas | Concluído |
| 4 | Compartilhamento de tarefas | Concluído |
| 5 | Busca, filtros avançados, ordenação e paginação | Concluído |
| 6 | Integração com o Google Calendar (OAuth2, sincronização de eventos) | Concluído |
| 7 | Integração com o Telegram Bot API (notificações) | Concluído |
| 8 | Deploy completo na AWS (Free Tier) | Pendente |
| 9 | CI/CD (GitHub Actions, Selenium, releases) | Pendente |
| 10 | Auditoria arquitetural final, documentação definitiva e release v1.0.0 | Pendente |
