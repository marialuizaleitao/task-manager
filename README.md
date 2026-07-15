# Task Manager

Aplicação web de gerenciamento de tarefas (To-Do List), desenvolvida como case técnico para demonstrar práticas profissionais de engenharia de software: arquitetura em camadas, containerização, testes automatizados e CI/CD.

> **Status atual:** Sprint 6 concluída — autenticação (JWT), categorias, CRUD de tarefas, compartilhamento, busca/filtros/ordenação avançados e integração com o Google Calendar funcionais no backend e no frontend.

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
│   │       └── google_calendar/   # App própria: models, oauth, client, service
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
│   │   ├── components/     # CategoryForm/List, TaskForm/List, TaskShareManager, ProtectedRoute
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

Sem `GOOGLE_OAUTH_CLIENT_ID`/`GOOGLE_OAUTH_CLIENT_SECRET`/`GOOGLE_TOKEN_ENCRYPTION_KEY` configurados, o restante do sistema continua funcionando normalmente — apenas a integração com o Google Calendar fica indisponível.

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

## Limitações conhecidas

- **Escopo `calendar.events` é sensível para o Google** e exigiria um processo de verificação do app para uso público (vídeo demonstrativo, política de privacidade hospedada, revisão manual). Para este projeto — um case técnico, não um produto com usuários reais — o app permanece deliberadamente em modo **Testing**: funciona normalmente para até 100 usuários adicionados manualmente como **Test users** na tela de consentimento OAuth, sem o custo do processo de verificação. Isso é uma decisão consciente, não uma falha.
- **Sem fila de tarefas em segundo plano (Celery está fora do escopo desta sprint)**: a sincronização é best-effort e síncrona. Uma falha de sincronização só é corrigida automaticamente na próxima operação sobre a mesma tarefa, não por um retry agendado.
- **Backoff de quota não implementado**: o cliente HTTP tem retry de conexão e timeout configuráveis, mas não implementa o backoff exponencial documentado pelo Google para respostas `429`/`5xx` de limite de quota — o volume de uso de um projeto de demonstração não justifica essa complexidade agora, mas fica registrado como débito técnico caso o volume de sincronizações cresça.
- **Um único calendário por usuário** (`calendar_id`, padrão `"primary"`): não há UI para escolher entre múltiplos calendários da conta Google.

## Testes

```bash
docker compose exec backend pytest -v
```

Nenhum teste chama o Google de verdade. `apps.integrations.google_calendar.tests` cobre OAuth (troca de código, refresh, `invalid_grant`, timeout, erro HTTP, resposta inválida), o cliente da Calendar API (criação/atualização/exclusão de evento, 401, 5xx, timeout), o `service` (best-effort, refresh automático de token, transições ao adicionar/remover `due_date`) e as views (connect/callback/status/toggle/disconnect) — usando `monkeypatch` sobre `httpx.post`/`httpx.Client.request` com objetos `httpx.Response` reais, sem rede. `apps.integrations.tests` cobre `crypto.py`, `registry.py` e `sync.py` isoladamente, com um provedor dublê (`MagicMock`). `apps/tasks/tests/test_google_calendar_sync.py` verifica que `TaskViewSet` aciona `sync_task` na ação certa, sem testar o provedor em si.

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
| 7 | Integração com o Telegram Bot API (notificações) | Pendente |
| 8 | Deploy completo na AWS (Free Tier) | Pendente |
| 9 | CI/CD (GitHub Actions, Selenium, releases) | Pendente |
| 10 | Auditoria arquitetural final, documentação definitiva e release v1.0.0 | Pendente |
