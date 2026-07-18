# Task Manager

Aplicação web de gerenciamento de tarefas (To-Do List), desenvolvida como case técnico para demonstrar práticas profissionais de engenharia de software: arquitetura em camadas, containerização, testes automatizados, CI/CD e deploy em produção na nuvem.

> **Status atual:** Sprint 11 em andamento — auditoria final, hardening, documentação definitiva e preparação da release `v1.0.0`. Sprints 0 a 10.1 concluídas: autenticação (JWT), cadastro e login, categorias, CRUD de tarefas, compartilhamento com controle de permissão, busca/filtros/ordenação avançados, integração com o Google Calendar, canal de comunicação via Telegram, deploy em produção na AWS, pipeline de CI/CD completo (GitHub Actions, Selenium, Dependabot) e refinamento de UI/UX.

## Sumário

- [Visão geral](#visão-geral)
- [Capturas de tela](#capturas-de-tela)
- [Stack tecnológica](#stack-tecnológica)
- [Arquitetura](#arquitetura)
- [Decisões arquiteturais e trade-offs](#decisões-arquiteturais-e-trade-offs)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Fluxo de trabalho Git](#fluxo-de-trabalho-git)
- [Como rodar](#como-rodar)
- [Deploy em produção (AWS)](#deploy-em-produção-aws)
- [Integração contínua e entrega (CI/CD)](#integração-contínua-e-entrega-cicd)
- [Como testar](#como-testar)
- [Performance](#performance)
- [Limitações conhecidas](#limitações-conhecidas)
- [Melhorias futuras](#melhorias-futuras)
- [Roadmap](#roadmap)
- [Como contribuir](#como-contribuir)
- [Autores](#autores)
- [Licença](#licença)

## Visão geral

Task Manager é uma aplicação completa de gerenciamento de tarefas: cada usuário cadastra, organiza por categoria, compartilha com outras pessoas (com controle de permissão de leitura ou edição), filtra, busca e ordena suas tarefas. Duas integrações externas ampliam o sistema além do CRUD básico — sincronização automática com o Google Calendar e notificações via Telegram —, nenhuma delas obrigatória para o funcionamento do restante da aplicação.

O projeto foi construído sprint a sprint, cada uma entregando uma versão funcional e testada, com as decisões arquiteturais documentadas e justificadas (não apenas descritas) ao longo deste README. O objetivo declarado é servir como case técnico: demonstrar como a arquitetura, os testes, a documentação e o pipeline de entrega de um projeto real profissional são estruturados — não como um exercício acadêmico isolado.

## Capturas de tela

> Seção reservada para capturas de tela da aplicação (login, cadastro, lista de tarefas, compartilhamento, painéis de integração). Ainda não preenchida nesta sprint — inclusão de imagens reais é um passo de documentação posterior à validação da interface já publicada em produção.

## Stack tecnológica

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
- Nginx (gateway único em produção: TLS termination, SPA, proxy para a API)
- Let's Encrypt / Certbot (HTTPS, renovação automática)
- AWS EC2 (Free Tier), Elastic IP, Security Groups, IAM
- Gunicorn (servidor WSGI de produção)
- GitHub Actions (CI/CD), GitHub Container Registry (imagens versionadas), Dependabot
- Selenium (testes end-to-end), pytest-cov (cobertura)

## Arquitetura

### Diagrama da arquitetura

```
                        ┌─────────────────────────┐
                        │        Navegador         │
                        └────────────┬─────────────┘
                                     │ HTTPS
                        ┌────────────▼─────────────┐
                        │           Nginx           │  gateway único (produção)
                        │  /  → SPA (React build)   │
                        │  /api → proxy              │
                        └────────────┬─────────────┘
                                     │
                     ┌───────────────▼────────────────┐
                     │       Django REST Framework      │
                     │  Views → Services → Models       │
                     │  JWT · permissions · filtros      │
                     └───────┬─────────────────┬────────┘
                             │                  │
                  ┌──────────▼─────────┐ ┌──────▼──────────────────┐
                  │     PostgreSQL       │ │   apps/integrations      │
                  │  (dados do domínio)  │ │  Google Calendar API      │
                  └─────────────────────┘ │  Telegram Bot API         │
                                          └───────────────────────────┘
```

Em desenvolvimento, o React roda em seu próprio servidor (Vite) e o Django expõe a API diretamente, sem Nginx no meio — ver "Arquitetura de produção" abaixo para o layout usado em produção.

### Fluxo do sistema

Um ciclo de vida típico de uma tarefa passa pelas seguintes camadas, na ordem:

1. **Cadastro e login** (`apps/accounts`): o usuário se registra, recebe um par de tokens JWT (`access`/`refresh`) e passa a autenticar toda chamada subsequente via `Authorization: Bearer`.
2. **Criação da tarefa** (`apps/tasks`): `TaskViewSet` valida os dados via serializer, persiste via `Task.objects.create()` e devolve a representação serializada.
3. **Efeitos colaterais best-effort** (`apps/integrations`): logo após a persistência, `sync_task()` tenta criar o evento correspondente no Google Calendar (se conectado) e `notify_task()` despacha uma notificação Telegram (se conectado) — nenhum dos dois pode fazer a criação da tarefa falhar.
4. **Organização** (`apps/categories`, `apps/sharing`): a tarefa pode ser categorizada e compartilhada com outros usuários, cada compartilhamento carregando seu próprio nível de permissão (`read`/`edit`).
5. **Consulta** (`apps/tasks/filters.py`): listagens combinam filtros (categoria, status, intervalo de datas), busca textual e ordenação, sempre restritas ao que o usuário autenticado pode ver.
6. **Conclusão ou exclusão**: marcar como concluída dispara uma notificação Telegram específica; excluir não dispara nenhuma (ver "Canal de comunicação do sistema" abaixo).

### Organização do backend

O backend segue separação em camadas:

```
Views → Services → Repositories (quando houver ganho real) → Models
```

Regras de negócio ficam concentradas em services quando há lógica real a isolar (ex.: `accounts.services.register_user`). Módulos com CRUD simples e sem orquestração adicional (`categories`, `tasks`) resolvem tudo em serializer + viewset, sem um service artificial. Repositories são introduzidos apenas quando reduzem acoplamento de forma concreta — ainda não há necessidade real no projeto.

Cada app Django tem uma responsabilidade única e não sobrepõe as demais:

| App | Responsabilidade |
|---|---|
| `apps/accounts` | Usuário customizado, JWT (login, refresh, logout), registro, endpoint `/me` |
| `apps/categories` | CRUD de categorias, escopado ao usuário dono |
| `apps/tasks` | CRUD de tarefas, filtros/busca/ordenação, ponto único de integração com `sync_task`/`notify_task` |
| `apps/sharing` | Compartilhamento de tarefas (`TaskShare`), permissão de acesso por ação |
| `apps/integrations` | Contrato comum a qualquer provedor externo (calendário, notificação), registry, despacho best-effort |
| `apps/integrations/google_calendar` | Provedor concreto: OAuth2, cliente REST, sincronização de eventos |
| `apps/integrations/telegram` | Provedor concreto: vinculação de conta, envio de mensagens, resumos |

### Organização do frontend

O frontend é organizado por responsabilidade (componentes, páginas, hooks, contextos e serviços de API), seguindo o mesmo princípio do backend: cada pasta só existe quando há conteúdo real que a justifique.

| Pasta | Responsabilidade |
|---|---|
| `pages/` | Uma página por rota (Login, Register, Home, Categories, Tasks, SharedTasks) — orquestra dados e composição de componentes |
| `components/` | Peças reutilizáveis (formulários, listas, painéis de integração) sem conhecimento de rota |
| `contexts/` | `AuthContext`/`AuthProvider` — estado de autenticação global |
| `hooks/` | Lógica reutilizável entre componentes, quando há reuso real |
| `services/` | Clientes de API por domínio (auth, categories, tasks, sharing) e utilitários comuns (paginação, armazenamento de token) |

Tipos genéricos reutilizados por mais de um serviço (ex.: resposta paginada) ficam em um módulo próprio (`services/pagination.ts`) em vez de duplicados.

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

Dois índices compostos (`Task.Meta.indexes`) foram adicionados na Sprint 5 — `(owner, due_date)` e `(owner, -created_at)` — depois de confirmar via `QuerySet.explain()` que filtrar ou ordenar por esses campos forçava um `TEMP B-TREE` mesmo após a redução por `owner_id` via índice. Nenhum outro índice foi criado: filtro por `completed` (baixa cardinalidade) e por `category` (já indexado pela FK) não mostraram esse padrão.

### Módulo de integrações e sincronização com o Google Calendar

A partir da Sprint 6, o projeto ganhou um módulo de integrações desenhado para múltiplos provedores externos, não apenas para o Google. `apps/integrations` concentra o que é comum a qualquer provedor:

- **`interfaces.py`** define `CalendarEventProvider` (`typing.Protocol`) com `is_connected`, `sync_create`, `sync_update` e `sync_delete`. `apps/tasks` depende apenas deste contrato.
- **`registry.py`** é um dicionário simples de provedores registrados por chave (`"google_calendar"` → `GoogleCalendarService`). Cada provedor se registra sozinho, no `ready()` do próprio `AppConfig`.
- **`sync.py`** expõe a única função que `apps/tasks` conhece para calendário: `sync_task(task, action)`. Ela percorre os provedores conectados via `registry` e delega a cada um — `apps/tasks` nunca importa `google_calendar` diretamente.
- **`exceptions.py`** define o vocabulário de erro compartilhado (`ExternalServiceError`, `AuthenticationExpiredError`, `ProviderNotConfiguredError`), para que `sync.py` trate qualquer provedor de forma genérica.
- **`crypto.py`** implementa `EncryptedTextField` (Fernet), reutilizável por qualquer credencial de integração futura.

Cada provedor concreto vive em sua própria app Django aninhada, com models e migrations independentes — `apps.integrations.google_calendar` é a primeira. Um futuro provedor de calendário (Outlook Calendar, Google Tasks) seguiria a mesma estrutura, sem tocar em `apps/tasks` nem nos demais provedores: só precisa implementar `CalendarEventProvider` e se registrar.

**Por que uma app Django por provedor, e não uma única app `integrations` com todos os models juntos:** cada provedor tem seu próprio ciclo de vida de schema. Se `GoogleCalendarCredential` e um futuro `OutlookCredential` dividissem o mesmo histórico de migrations, remover ou substituir um provedor exigiria mexer no histórico do outro. Apps aninhadas com migrations próprias tornam cada integração genuinamente independente.

#### Fluxo OAuth2 (Google Calendar)

Fluxo Authorization Code ("Web Server Flow"): o usuário é redirecionado para `accounts.google.com`, autoriza o escopo `calendar.events` (não o acesso completo à agenda — princípio do menor privilégio) e o Google devolve um `code` para `GET /callback/`. Como esse redirect é uma navegação de navegador comum, sem `Authorization: Bearer`, o usuário é identificado por um `state` assinado (`django.core.signing`, expira em 10 minutos) em vez de JWT. O backend troca o `code` por `access_token` + `refresh_token` em `oauth2.googleapis.com/token`, usando `access_type=offline` e `prompt=consent` para garantir que o `refresh_token` seja sempre emitido. Um `access_token` expirado é renovado automaticamente antes de cada chamada (`GoogleCalendarService._ensure_valid_token`); se o Google responder `invalid_grant`, isso é tratado como necessidade de nova autorização — nunca como erro fatal.

**Cliente HTTP — `httpx` próprio em vez do SDK oficial do Google:** o projeto já usa `httpx` como padrão de cliente HTTP (decisão herdada de sprints anteriores: timeouts de primeira classe, tipagem, `HTTPTransport` com retry declarativo). O SDK oficial (`google-api-python-client`) resolve endpoints via *discovery* dinâmico em runtime, o que tornaria o fluxo OAuth2 menos explícito e adicionaria uma segunda forma de fazer HTTP no projeto. Um cliente próprio (`google_calendar/client.py` e `oauth.py`), consumindo a REST API v3 diretamente, mantém consistência arquitetural e reaproveita o mesmo tratamento de erro das demais camadas.

**Síncrono, não assíncrono:** o restante do backend (Django + DRF clássico, sem ASGI) é inteiramente síncrono; introduzir chamadas assíncronas apenas nesta integração exigiria uma ponte `async`/`sync` sem nenhum ganho real, já que a sincronização acontece dentro do ciclo request/response de uma única operação de tarefa.

**Sincronização best-effort, nunca bloqueante:** `TaskViewSet.perform_create/perform_update/perform_destroy` chamam `sync_task` depois que a tarefa já foi persistida no banco. Qualquer falha do Google (timeout, 401, 5xx, indisponibilidade) é capturada dentro do próprio provedor — que registra `status` (`pending`/`synced`/`failed`), `last_error` e `last_synced_at` em `GoogleCalendarEventLink` — e por `sync.py`, que nunca deixa uma exceção escapar para a view. A criação, edição ou remoção de uma tarefa **nunca** falha por causa do Google estar fora do ar. Sem uma fila (Celery está fora do escopo), não há retry automático em segundo plano — uma falha só é corrigida na próxima operação sobre a mesma tarefa (`sync_update` detecta um vínculo sem `google_event_id` e tenta criar novamente).

**Eventos de dia inteiro:** só tarefas com `due_date` sincronizam. O Google trata o fim de eventos de dia inteiro como exclusivo, então `due_date` vira `start.date = due_date` e `end.date = due_date + 1 dia`.

**Seam para cache futuro, sem Redis:** o ponto de extensão é `GoogleCalendarService` — por exemplo, cachear se um `google_event_id` já existe antes de decidir entre criar (`POST`) ou atualizar (`PATCH`). Nenhuma mudança na interface `CalendarEventProvider` seria necessária; `apps/tasks` e `sync.py` não saberiam que o cache existe.

**Retries e timeout:** `GoogleCalendarClient` usa `httpx.HTTPTransport(retries=GOOGLE_API_MAX_RETRIES)`, que cobre falhas de conexão (DNS, timeout de conexão) — não substitui o backoff exponencial documentado pelo Google para respostas `429`/`5xx` de quota, que exigiria uma fila para ser feito com segurança fora do ciclo request/response e fica registrado como débito técnico. O timeout (`GOOGLE_API_TIMEOUT_SECONDS`, padrão 10s) limita o pior caso de latência adicionada à criação/edição de uma tarefa.

### Canal de comunicação do sistema (Telegram como primeiro provedor)

A Sprint 7 introduziu o Telegram como um "sistema de notificações de tarefa". A Sprint 7.1 generalizou esse conceito: o Telegram passou a ser o primeiro provedor de um **canal oficial de comunicação do sistema**, capaz de representar eventos de qualquer domínio — não apenas de `Task` — sem exigir mudança na interface pública sempre que um novo tipo de evento surgir. O fluxo passou a ser `Sistema → Canal de Comunicação → Telegram` em vez de `Task → Telegram`.

**O que mudou e por quê:**

- **`interfaces.py`**: `TaskNotificationProvider` foi renomeado para **`NotificationProvider`**, e seus três métodos por evento (`notify_task_created`/`notify_task_completed`/`notify_task_overdue`) foram substituídos por um único `notify(event: NotificationEvent)`. A forma anterior acoplava a interface ao domínio `Task`: cada novo tipo de evento exigiria um novo método no Protocol e em toda implementação, mesmo nas que não usam aquele evento. Um único `notify(event)` resolve isso — a interface pública nunca muda, apenas o catálogo de eventos que cada provedor sabe formatar. Das três opções avaliadas (`MessagingProvider`, `CommunicationProvider`, `NotificationProvider`), `NotificationProvider` foi escolhida: o sistema continua fazendo comunicação unidirecional (sistema → usuário, "fire-and-forget"), nunca conversação bidirecional — `CommunicationProvider` sugeriria uma capacidade de troca de mensagens que o projeto não tem e não precisa; `MessagingProvider` descreveria o transporte ("enviar mensagens"), não a semântica ("avisar sobre um evento"). `NotificationProvider` é o nome que corresponde exatamente ao que o provedor faz, sem prometer mais do que isso.
- **`NotificationEvent`** (`interfaces.py`): um `dataclass` com `key` (string com namespace pontilhado, ex. `"task.created"`, `"task.shared"`, `"calendar.sync_failed"`), `user` (destinatário), `subject` (o objeto de domínio ao qual o evento se refere — hoje sempre uma `Task`) e `context` (dados que não vêm de `subject` sozinho, ex. quem fez uma alteração). Um evento com múltiplos destinatários (ex. "tarefa compartilhada foi atualizada", que avisa vários usuários afetados) é despachado como múltiplos `NotificationEvent`, um por destinatário — mantém `notify()` de destinatário único, sem exigir que cada provedor implemente sua própria lógica de fan-out.
- **`registry.py`**: sem mudança de forma, apenas de tipo (`NotificationProvider` no lugar de `TaskNotificationProvider`).
- **`notifications.py`**: expõe `notify(event)`, o despacho genérico de fato — percorre os provedores de notificação conectados e delega a cada um, isolando a falha de um provedor dos demais (mesmo contrato best-effort das demais integrações). É o ponto de entrada para *qualquer* domínio futuro (autenticação, comentários, organizações, auditoria) que precise notificar um usuário, sem depender de nada específico de `Task`.
- **`sync.py`**: continua sendo o módulo que `apps/tasks` conhece, mas agora é só um conjunto de atalhos sobre `notifications.notify()` — `notify_task(task, event)` (compatível com a assinatura da Sprint 7), `notify_task_shared(share)` e `notify_task_shared_updated(task, actor)`. `sync_task` (calendário) não foi tocado.
- **`telegram/messages.py`**: catálogo de mensagens — um dicionário simples de `event.key` para uma função formatadora, centralizando toda a formatação de texto que antes vivia solta em `service.py`. Deliberadamente escopado ao Telegram: um `communication/templates.py` compartilhado entre provedores foi avaliado e descartado, porque hoje só existe um provedor — criar essa camada agora seria generalizar sem um segundo caso de uso real para validar a abstração (formato ideal de mensagem difere por canal: texto simples aqui, *blocks* estruturados em um futuro Slack, HTML em um futuro e-mail).
- **`telegram/service.py`**: `TelegramService` agora implementa apenas `notify(event)` — que aplica a única regra de negócio que permanece fora do catálogo de mensagens (uma tarefa sem `due_date` não gera notificação de criação) e delega a formatação para `messages.py`. `DailySummaryService` foi enriquecido e `WeeklySummaryService` foi adicionado (ver "Resumos" abaixo).

**O que permaneceu sem mudança:** a modelagem de `TelegramConnection`, a justificativa de segurança do `telegram_chat_id` não criptografado, o fluxo de vinculação via deep link, a ausência de offset persistente em `getUpdates`, o comportamento best-effort de toda notificação, e a desabilitação automática da conexão quando o chat fica inalcançável.

**Eventos do catálogo:**

- **`task.created`**: só quando há `due_date`.
- **`task.completed`**: ao marcar uma tarefa como concluída.
- **`task.overdue`**: implementado e testado, sem disparo automático (ver "Limitações conhecidas").
- **`task.shared`**: disparado quando uma tarefa é compartilhada (`POST /api/tasks/{id}/shares/`), notificando o usuário com quem ela foi compartilhada. `context["permission"]` carrega o nível de acesso (`read`/`edit`), formatado via `TaskShare.Permission(...).label`.
- **`task.shared_updated`**: disparado quando uma tarefa com compartilhamentos ativos é atualizada, por qualquer pessoa (dono ou colaborador). Os destinatários são o dono mais todos os usuários com quem a tarefa está compartilhada, **exceto quem fez a própria alteração**.
- **`calendar.sync_succeeded` / `calendar.sync_failed`**: `GoogleCalendarService._call()` notifica o dono da tarefa ao final de cada tentativa de sincronização. Exclusões deliberadas antes de excluir um evento do calendário não disparam notificação, em sucesso nem em falha — a tarefa já está prestes a ser removida de qualquer forma.

**Resumos (`telegram/service.py`):**

- **`DailySummaryService`**: mensagem com três contadores (pendentes, vencendo hoje, atrasadas). Sem disparo automático — não há scheduler (ver "Performance").
- **`WeeklySummaryService`**: resumo semanal (criadas, concluídas, compartilhadas, atrasadas) via `build_message(user)`. Apenas o serviço existe; não há disparo automático, por decisão explícita de escopo. "Concluídas" usa `updated_at` como aproximação de quando a tarefa foi concluída — `Task` não tem um campo `completed_at` dedicado (ver "Limitações conhecidas").

### Arquitetura de produção

```
Internet → Elastic IP → Nginx (80/443, TLS termination)
                          ├── /            → build estático do React
                          ├── /static/     → estáticos do Django (ex.: browsable API do DRF)
                          └── /api/        → proxy → Gunicorn
Gunicorn (backend) → PostgreSQL (container na rede interna, sem porta pública)
Gunicorn (backend) → Google Calendar API / Telegram Bot API
Certbot → renova o certificado Let's Encrypt automaticamente
```

Tudo roda em uma única instância EC2 (t3.micro, Free Tier), orquestrado por `docker-compose.prod.yml`. Guia completo, do zero, em [`docs/deploy-aws.md`](docs/deploy-aws.md).

**Um único gateway Nginx, não dois processos separados:** antes da Sprint 8, o container `frontend` era um Nginx sem nenhum conhecimento do backend (só servia a SPA), e o backend expunha a porta 8000 diretamente. Consolidar em um único Nginx que também faz proxy de `/api/` elimina CORS em produção (frontend e API passam a ser a mesma origem do ponto de vista do navegador) e remove a necessidade de expor o Gunicorn publicamente — o backend só é alcançável pela rede interna do Docker.

**PostgreSQL em Docker Compose na própria EC2, não Amazon RDS:** o Free Tier de RDS mudou em julho de 2025 — contas novas não têm mais cobertura gratuita de RDS Postgres tradicional (só Aurora Serverless por ~6 meses); contas legadas mantêm 750h/mês de `db.t3.micro`, mas isso não é garantido para quem for reproduzir este projeto. Rodar Postgres no mesmo Compose elimina essa incerteza de custo, mantém paridade total com o ambiente de desenvolvimento (mesma imagem `postgres:18-alpine`) e reproduz com um único `docker compose up`. Para este porte de projeto — um case técnico de instância única — o ganho de um banco gerenciado (backups automáticos, failover) não compensa o custo e a complexidade adicional de provisionar e documentar um segundo serviço AWS.

**DuckDNS em vez de Route 53:** Let's Encrypt não emite certificado para IP puro — é necessário um hostname. Route 53 custa ~US$0,50/mês por zona hospedada mais o custo do domínio em si; sem domínio próprio hoje, um subdomínio gratuito do DuckDNS resolve o mesmo problema sem custo recorrente. Trocar para um domínio próprio no futuro é só apontar o registro A e ajustar `DOMAIN_NAME` — nenhuma outra mudança de arquitetura.

**Certbot via serviço do próprio Compose, não `nginx-proxy` + `acme-companion`:** o projeto já teria essa automação pronta com ferramentas de terceiros, mas ao custo de menos controle explícito sobre a configuração do Nginx — o serviço `certbot` do `docker-compose.prod.yml` roda em loop, verificando a cada 12h se o certificado precisa renovar, sem esconder nenhum passo do processo.

**Gunicorn tunado para uma instância t3.micro (1 vCPU / 1 GiB RAM):** `GUNICORN_WORKERS=2` (a fórmula usual `2 * vCPU + 1` competiria demais por memória com Postgres e Nginx nesse porte de instância), `--timeout 30s` (folga acima do timeout de 10s configurado para as chamadas ao Google/Telegram) e `--keep-alive 5s`. Sem Redis — nenhum cache HTTP adicional foi introduzido; os únicos caches de resposta são os `Cache-Control` do Nginx para assets estáticos, já que respostas da API são sempre dinâmicas/autenticadas e não deveriam ser cacheadas.

**Segurança:** `SECURE_PROXY_SSL_HEADER` (`config/settings/prod.py`) informa ao Django que a requisição chegou em HTTPS mesmo vindo do Nginx em HTTP puro internamente — sem isso, `SECURE_SSL_REDIRECT` entraria em loop de redirecionamento. HSTS (1 ano, sem preload — entrar na lista de preload dos navegadores é difícil de reverter), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` e `Referrer-Policy` são aplicados tanto pelo Django quanto pelo Nginx (defesa em profundidade). `CSRF_TRUSTED_ORIGINS` é explícito — a API em si usa JWT (sem CSRF), mas a proteção do Django permanece ativa por padrão para qualquer view futura autenticada por sessão. O container `backend` roda em produção como usuário não-root (`app`, criado no Dockerfile), e a API tem *rate limiting* por IP/usuário (`DEFAULT_THROTTLE_RATES`, ver "Decisões arquiteturais e trade-offs").

**Logs:** logs de aplicação (`gunicorn-access.log`/`gunicorn-error.log`, volume `backend_logs`) ficam separados dos logs do Nginx (volume `nginx_logs`) — nenhuma ferramenta de observabilidade (Prometheus, Grafana) foi introduzida, por estar fora do escopo definido (ver "Melhorias futuras"); a separação em volumes próprios já deixa a estrutura pronta para um agente de coleta ser plugado no futuro sem reorganizar nada.

## Decisões arquiteturais e trade-offs

Resumo indexado das decisões mais relevantes — cada uma detalhada na seção correspondente acima:

| Decisão | Alternativa considerada | Por quê |
|---|---|---|
| `TaskShare` como tabela própria | `ManyToManyField(through=...)` ou ACL genérica via `contenttypes` | Toda consulta relevante já precisa do `permission` junto do usuário; ACL genérica seria abstração prematura para um único recurso compartilhável |
| `FilterSet` declarativo em `tasks`, `if` simples em `categories` | `FilterSet` em todo lugar | `tasks` tem 6 filtros combináveis; `categories` tem 1 — a complexidade do `FilterSet` só se paga a partir de um certo número de filtros |
| App Django própria por provedor de integração | Uma única app `integrations` com todos os models | Cada provedor tem seu próprio ciclo de vida de schema/migrations; acoplar isso dificultaria remover ou substituir um provedor |
| `httpx` próprio em vez do SDK oficial do Google | `google-api-python-client` | Mantém um único padrão de cliente HTTP no projeto (timeouts, retry, tipagem); o SDK oficial usa *discovery* dinâmico, tornando o OAuth2 menos explícito |
| Sincronização best-effort e síncrona, sem fila | Celery + retry automático | A criação de uma tarefa nunca deve falhar por causa de um serviço externo; uma fila resolveria retries, mas está fora do escopo desta versão |
| `NotificationProvider.notify(event)` único | Um método por tipo de evento | Evita que a interface mude a cada novo tipo de evento; o catálogo de mensagens (`messages.py`) é que decide o que cada provedor sabe formatar |
| Postgres em Docker Compose na EC2 | Amazon RDS | RDS deixou de ter Free Tier tradicional para contas novas (jul/2025); rodar no mesmo Compose elimina essa incerteza de custo e mantém paridade dev/produção |
| Nginx único como gateway (proxy de `/api`) | Dois processos/portas separados | Elimina CORS em produção (mesma origem) e remove a necessidade de expor o Gunicorn publicamente |
| DuckDNS em vez de Route 53 | Zona hospedada Route 53 | Certificado Let's Encrypt exige um hostname; DuckDNS resolve isso sem custo recorrente enquanto não há domínio próprio |
| `django.contrib.admin` removido do projeto | Manter a rota `/admin/` sem uso | Nenhum `admin.py` jamais registrou um model — a rota era superfície de ataque sem nenhum ganho real. Removida na Sprint 11: `INSTALLED_APPS`, `urlpatterns`, proxy no Nginx e `collectstatic` não a conhecem mais |

## Estrutura do projeto

```
task-manager/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml           # testes, lint, build, Selenium, validação Docker
│   │   ├── publish.yml      # publica imagens no GitHub Container Registry
│   │   ├── release.yml      # manual: tag + Release a partir do CHANGELOG
│   │   └── deploy.yml       # manual: registra os Environments no GitHub
│   └── dependabot.yml
├── e2e/                      # suíte Selenium (fora de backend/, outro runtime)
├── backend/
│   ├── apps/
│   │   ├── accounts/       # Custom User, JWT, registro, login, /me
│   │   ├── categories/     # CRUD de categorias
│   │   ├── tasks/          # CRUD de tarefas, filtros (filters.py)
│   │   ├── sharing/        # Compartilhamento de tarefas (TaskShare, permissions)
│   │   └── integrations/   # Módulo de integrações externas
│   │       ├── interfaces.py, registry.py, sync.py, notifications.py, exceptions.py, crypto.py
│   │       ├── google_calendar/   # App própria: models, oauth, client, service
│   │       └── telegram/          # App própria: models, client, service, messages, views
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
│       └── nginx.conf.template   # gateway de produção (envsubst em $DOMAIN_NAME)
├── docs/
│   └── deploy-aws.md        # guia completo de deploy na AWS, do zero
├── docker-compose.yml
├── docker-compose.prod.yml
├── .dockerignore
├── .env.example              # desenvolvimento
├── .env.prod.example         # produção
├── CHANGELOG.md
└── README.md
```

## Fluxo de trabalho Git

### Branches

```
master → develop → feature/*
```

Nenhum commit é feito diretamente em `master`. Funcionalidades são desenvolvidas em branches `feature/*`, `fix/*`, `refactor/*`, `docs/*` ou `test/*`, com Pull Request para `develop`. Merges de `develop` para `master` ocorrem apenas após um conjunto estável e testado de funcionalidades. Todo Pull Request para `develop` ou `master` passa obrigatoriamente pelo pipeline de CI (ver "Integração contínua e entrega") antes de poder ser mesclado — desde que a branch protection recomendada seja ativada nas configurações do repositório.

### Conventional Commits

Commits seguem [Conventional Commits](https://www.conventionalcommits.org/) — `feat`, `fix`, `refactor`, `docs`, `test`, `ci`, `build`, `chore`, sempre com um escopo entre parênteses quando fizer sentido (ex.: `feat(auth): implement JWT authentication`).

### Versionamento

O projeto adota [Versionamento Semântico](https://semver.org/lang/pt-BR/) (`MAJOR.MINOR.PATCH`). `CHANGELOG.md` segue o formato [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), atualizado a cada conjunto de mudanças relevante. A primeira versão marcada (`v1.0.0`) está sendo preparada nesta sprint — ver "Roadmap" e o `CHANGELOG.md` para o que ela contém.

## Como rodar

Pré-requisitos: Docker e Docker Compose instalados.

### Variáveis de ambiente

Desenvolvimento usa `.env.example`; produção usa `.env.prod.example` (valores adicionais/diferentes documentados em cada seção do arquivo). Copie o arquivo correspondente para `.env` antes de subir o projeto:

```bash
cp .env.example .env          # desenvolvimento
# ou
cp .env.prod.example .env     # produção (ver docs/deploy-aws.md)
```

| Variável | Descrição |
|---|---|
| `DJANGO_SETTINGS_MODULE` | Módulo de settings ativo (`config.settings.dev` ou `config.settings.prod`) |
| `DJANGO_SECRET_KEY` | Chave secreta do Django |
| `DJANGO_DEBUG` | Ativa/desativa modo debug |
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos, separados por vírgula |
| `DOMAIN_NAME` | *(produção)* domínio público, interpolado no template do Nginx |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | *(produção)* origens confiáveis para CSRF (ex. `https://seu-dominio`) |
| `DJANGO_SECURE_SSL_REDIRECT` / `DJANGO_SECURE_HSTS_SECONDS` | *(produção)* redirect HTTPS e duração do HSTS |
| `CORS_ALLOWED_ORIGINS` | Origens permitidas para requisições CORS (vazio em produção — mesma origem via proxy) |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | Credenciais do banco |
| `POSTGRES_HOST` / `POSTGRES_PORT` | Endereço do banco |
| `VITE_API_URL` | URL base da API consumida pelo frontend (`/api` em produção, embutido no build) |
| `GUNICORN_WORKERS` / `GUNICORN_TIMEOUT` / `GUNICORN_KEEPALIVE` | *(produção)* tuning do Gunicorn |
| `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` | Credenciais do OAuth Client do Google Cloud |
| `GOOGLE_OAUTH_REDIRECT_URI` | URL de callback do backend, cadastrada no Google Cloud |
| `GOOGLE_TOKEN_ENCRYPTION_KEY` | Chave Fernet para cifrar tokens OAuth em repouso |
| `FRONTEND_BASE_URL` | URL do frontend para onde o navegador retorna após o fluxo OAuth |
| `TELEGRAM_BOT_TOKEN` | Token do bot Telegram, obtido com o @BotFather — nunca armazenado no banco |

Sem `GOOGLE_OAUTH_CLIENT_ID`/`GOOGLE_OAUTH_CLIENT_SECRET`/`GOOGLE_TOKEN_ENCRYPTION_KEY` configurados, o restante do sistema continua funcionando normalmente — apenas a integração com o Google Calendar fica indisponível.

Sem `TELEGRAM_BOT_TOKEN` configurado, o restante do sistema também continua funcionando normalmente — apenas o canal de comunicação fica indisponível (`ProviderNotConfiguredError`, retornado como 503 pelos endpoints `telegram/*`).

### Execução com Docker

```bash
cp .env.example .env
docker compose up --build
docker compose exec backend python manage.py migrate
```

- Backend: http://localhost:8000/api/health/
- Frontend: http://localhost:5173

### Configurar o Google Cloud (integração com o Google Calendar)

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

#### Solução de problemas

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

### Criar um Bot no Telegram (canal de comunicação do sistema)

1. No Telegram, inicie uma conversa com **[@BotFather](https://t.me/BotFather)**.
2. Envie `/newbot` e siga as instruções: escolha um nome de exibição e um `username` terminado em `bot` (ex.: `task_manager_bot`).
3. O BotFather devolve o **token do bot** (formato `123456789:AAH...`). Copie-o para `TELEGRAM_BOT_TOKEN` no `.env` — nunca o compartilhe nem o versione.
4. Reconstrua o container do backend para que a nova variável seja lida (`docker compose up -d --force-recreate backend`, mesma ressalva da seção anterior).

#### Fluxo de vinculação (como vincular sua conta)

Um bot não pode iniciar contato com um usuário — só pode responder depois que o próprio usuário envia a primeira mensagem (restrição da própria Bot API, pensada contra spam). Por isso a vinculação usa um código de uso único em vez de simplesmente informar um `@username`:

1. Na página de tarefas do frontend, na seção **Telegram**, clique em **Conectar Telegram**. Isso abre, em uma nova aba, o deep link `https://t.me/<bot>?start=<código>`.
2. No Telegram, envie a mensagem `/start <código>` que já vem preenchida ao abrir o link (basta clicar em **Iniciar**).
3. De volta ao frontend, clique em **Verificar conexão**. O backend consulta `getUpdates`, localiza sua mensagem e conclui a vinculação.

#### Endpoints

Todos exigem autenticação JWT (`Authorization: Bearer <token>`), como o restante da API.

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/integrations/telegram/connect/` | Gera um novo `linking_code` e retorna o deep link do bot |
| `POST` | `/api/integrations/telegram/confirm/` | Verifica se o `/start <código>` já chegou e finaliza a vinculação |
| `GET` | `/api/integrations/telegram/status/` | Retorna `connected`, `telegram_username`, `enabled`, `last_contact_at` |
| `POST` | `/api/integrations/telegram/toggle/` | Habilita/desabilita notificações (`{"enabled": true/false}`) sem desvincular |
| `DELETE` | `/api/integrations/telegram/disconnect/` | Remove a vinculação — nenhuma mensagem é enviada depois disso |

#### Exemplos de mensagem

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

Tarefa vencida (implementado e testado, sem disparo automático — ver "Limitações conhecidas"):

```
⚠️ Tarefa vencida

Título:
Enviar documentação

Prazo:
20/07/2026
```

Tarefa compartilhada com você:

```
🔗 Uma tarefa foi compartilhada com você.

Título:
Enviar documentação

Permissão:
Edição
```

Tarefa compartilhada foi atualizada (enviado a todos os afetados, exceto quem fez a alteração):

```
🔄 Uma tarefa compartilhada foi atualizada.

Alterado por:
maria@example.com

Novo prazo:
20/07/2026

Status:
Pendente
```

Sincronização com o Google Calendar (sucesso):

```
Google Calendar

Sua tarefa foi sincronizada.
Evento criado com sucesso.

Título:
Enviar documentação
```

Sincronização com o Google Calendar (falha):

```
Google Calendar

Não foi possível sincronizar sua tarefa.
Sua tarefa continua salva normalmente.

Título:
Enviar documentação
```

## Deploy em produção (AWS)

Guia completo, do zero (conta AWS, EC2, HTTPS, deploy e rollback), em [`docs/deploy-aws.md`](docs/deploy-aws.md). Localmente, a stack de produção pode ser exercitada com:

```bash
cp .env.prod.example .env   # ajuste os valores antes
docker compose -f docker-compose.prod.yml up --build
```

O container `backend` aplica `migrate` e `collectstatic` automaticamente no start (`backend/docker-entrypoint.prod.sh`) — não é necessário rodá-los manualmente a cada subida.

## Integração contínua e entrega (CI/CD)

Todo Pull Request para `develop` ou `master` roda automaticamente o workflow `.github/workflows/ci.yml`, com quatro jobs independentes (falha em qualquer um bloqueia o merge, se a branch protection estiver configurada — ver abaixo):

- **`backend`**: sobe um Postgres via service container, instala as dependências de `backend/requirements/dev.txt`, roda `manage.py check`, `makemigrations --check --dry-run`, e a suíte `pytest` com cobertura (`pytest-cov`), gerando um relatório XML publicado como artefato e enviado ao Codecov de forma best-effort (não derruba o pipeline se o token não estiver configurado). Falha se a cobertura cair abaixo de 95%.
- **`frontend`**: instala as dependências com `npm ci`, roda `npm run lint` (oxlint) e `npm run build`.
- **`e2e`**: depende dos dois anteriores. Sobe um segundo Postgres, aplica as migrations, inicia o backend (`manage.py runserver`) e o frontend buildado (`vite preview`) como processos em background, espera os dois responderem e roda a suíte Selenium (`e2e/`) contra Chrome headless.
- **`docker`**: builda as quatro imagens (backend e frontend, alvos `dev` e `prod`) sem publicar, e valida a sintaxe dos dois `docker-compose` (`config -q`) usando os arquivos `.env.example`/`.env.prod.example`.

### Como interpretar o status do pipeline

Cada job aparece individualmente na aba **Checks** do Pull Request. Um X vermelho em `backend` quase sempre é teste ou migration faltando; em `frontend`, lint ou erro de tipo; em `e2e`, alguma regressão visível na integração entre frontend e backend (o job sobe os logs de backend/frontend como artefato quando falha); em `docker`, algo que quebra o build da imagem. Nenhum PR deveria ser mesclado com qualquer check vermelho.

### Publicação de imagens (CD)

`.github/workflows/publish.yml` builda e publica `backend` e `frontend` (alvo `prod`) no GitHub Container Registry a cada push em `master` e a cada tag `v*.*.*`, com as tags `latest` (só na branch padrão), `sha-<curto>` (sempre) e a própria tag de release (quando aplicável). Não roda em Pull Request — só depois que o código já foi revisado e mesclado.

### Dependabot

`.github/dependabot.yml` verifica semanalmente atualizações de `pip` (backend), `npm` (frontend) e `github-actions`, abrindo PRs contra `develop` — que passam pelo mesmo pipeline de CI que qualquer outra mudança.

### Releases

`.github/workflows/release.yml` só roda via disparo manual (`workflow_dispatch`): valida o formato da versão, confirma que existe a seção correspondente no `CHANGELOG.md`, cria a tag e a Release no GitHub a partir dela. Nenhuma Release foi criada ainda — a `v1.0.0` está sendo preparada nesta sprint (ver "Roadmap").

### Deployments e Environments

`.github/workflows/deploy.yml` também só roda via disparo manual e não executa nenhum deploy de verdade — existe apenas para que o GitHub reconheça os Environments `development` e `production` e passe a rastrear deployments na aba correspondente do repositório. O deploy continua manual, seguindo [`docs/deploy-aws.md`](docs/deploy-aws.md).

Antes de usar os Environments de verdade, crie-os em **Settings → Environments** e cadastre os secrets abaixo (nunca em texto plano no repositório):

| Secret | Uso |
|---|---|
| `DJANGO_SECRET_KEY` | Chave secreta do Django em produção |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | Credenciais do banco de produção |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Credenciais OAuth do Google Cloud |
| `GOOGLE_TOKEN_ENCRYPTION_KEY` | Chave Fernet para os tokens OAuth |
| `TELEGRAM_BOT_TOKEN` | Token do bot Telegram |
| `DUCKDNS_TOKEN` | Token da conta DuckDNS, caso a atualização de DNS venha a ser automatizada |
| `CODECOV_TOKEN` | Opcional — só necessário se o repositório for privado |

### Branch protection recomendada

Não configurada nesta sprint (mudança de configuração do repositório, não de código) — só documentada aqui. Em **Settings → Branches**, para `develop` e `master`:

- Require a pull request before merging
- Require status checks to pass before merging (os quatro jobs de `ci.yml`)
- Require conversation resolution before merging
- Require linear history
- Do not allow bypassing the above settings

## Como testar

```bash
docker compose exec backend pytest -v
```

**Rodando fora do Docker:** `POSTGRES_HOST` no `.env` é `db`, o nome do serviço na rede interna do Compose — só resolve dentro de um container. Para rodar `pytest` nativo (Windows, Linux ou macOS, fora do `docker compose exec`), suba apenas o banco e aponte para `localhost` (a porta 5432 já é publicada em `docker-compose.yml`):

```bash
docker compose up -d db
POSTGRES_HOST=localhost pytest --cov=apps --cov=config --cov-report=term-missing
```

No PowerShell, defina a variável com `$env:POSTGRES_HOST="localhost"` antes do comando. Sem isso, a suíte inteira falha com `OperationalError: failed to resolve host 'db'` — e, com `pytest-cov` instrumentado, esse tipo de falha em massa também aparece como uma cobertura artificialmente baixa (a maior parte do código nunca chega a ser exercitada), não é uma regressão real.

**Conflito de porta com um PostgreSQL local:** se a conexão falhar com `FATAL: password authentication failed for user "task_manager"` mesmo com `.env`, volume do Compose e credenciais todos conferidos, o suspeito mais provável é outro processo já escutando na porta 5432 do host — tipicamente um PostgreSQL instalado nativamente (Windows, Linux ou macOS), rodando como serviço e capturando a conexão antes dela chegar ao container `db`. Sintoma característico: `docker compose exec db env | grep POSTGRES` mostra as credenciais corretas, mas qualquer conexão feita de fora do container (via `psql`, `psycopg` ou o `pytest`) é recusada, porque na verdade nunca chega no Postgres do projeto. Para confirmar, identifique quem está na porta:

```bash
netstat -ano | findstr 5432   # Windows
sudo lsof -i :5432             # Linux/macOS
```

Se aparecer um `postgres`/`postgres.exe` além do processo do Docker, pare o serviço nativo (`net stop <nome-do-serviço>` no Windows, ou o equivalente via `systemctl`/`brew services` em Linux/macOS) e suba o `db` novamente. Alternativa, caso o Postgres local seja usado por outro projeto e não possa ser parado: publicar o serviço `db` em uma porta diferente (ex.: `5433:5432` em `docker-compose.yml`) e ajustar `POSTGRES_PORT` no `.env` de acordo — a rede interna do Compose continua usando 5432 normalmente, essa mudança afeta só o acesso pelo host.

Além da suíte de unidade do Django, `e2e/` contém uma suíte Selenium (registro, login, ciclo de vida de uma tarefa) que dirige um navegador real contra o frontend buildado e o backend rodando de verdade — ver "Integração contínua e entrega" acima para como ela roda no pipeline. Para rodar localmente, com backend e frontend já de pé (`docker compose up`, portas 8000 e 5173):

```bash
pip install -r e2e/requirements.txt
E2E_BASE_URL=http://localhost:5173 pytest e2e -v
```

Nenhum teste chama o Google ou o Telegram de verdade. `apps.integrations.google_calendar.tests` cobre OAuth (troca de código, refresh, `invalid_grant`, timeout, erro HTTP, resposta inválida), o cliente da Calendar API (criação/atualização/exclusão de evento, 401, 5xx, timeout), o `service` (best-effort, refresh automático de token, transições ao adicionar/remover `due_date`, e o disparo de `calendar.sync_succeeded`/`calendar.sync_failed`) e as views (connect/callback/status/toggle/disconnect). `apps.integrations.telegram.tests` cobre o `TelegramClient` (`getMe`, `sendMessage`, `getUpdates`, 401, chat bloqueado/inexistente, timeout, erro de rede, JSON inválido), o `TelegramService.notify()` para cada evento do catálogo, `DailySummaryService` e `WeeklySummaryService` — com a mesma estratégia de `monkeypatch` sobre a classe `TelegramClient`, nenhuma chamada HTTP real. `apps.integrations.tests` cobre `crypto.py`, `registry.py` (os dois registries independentes) e `sync.py`/`notifications.py` isoladamente, com provedores dublês (`MagicMock`). `apps/tasks/tests/test_google_calendar_sync.py`, `apps/tasks/tests/test_telegram_notifications.py` e `apps/tasks/tests/test_sharing_notifications.py` verificam que `TaskViewSet` aciona `sync_task`/`notify_task`/`notify_task_shared`/`notify_task_shared_updated` nos pontos certos, sem testar os provedores em si.

### Cobertura

Cobertura medida com `pytest-cov` (`.coveragerc`): **98%** sobre `apps/` e `config/`, 265 testes (migrations, testes e os módulos de settings de dev/prod, não exercitados pelo settings de teste, ficam de fora da medição por não serem testáveis dessa forma — validados via `manage.py check --deploy` e pelo build Docker). O pipeline de CI falha se a cobertura cair abaixo de 95%. As linhas não cobertas são, quase todas, `__str__` de models e corpos de `Protocol` (`...`), que não carregam lógica testável.

```bash
docker compose exec backend pytest --cov=apps --cov=config --cov-report=term-missing
```

## Performance

**Por que polling (`getUpdates`) em vez de webhook:** um webhook exigiria um endpoint HTTPS publicamente acessível, com certificado válido, para o qual o Telegram enviaria atualizações via `POST` — viável apenas após o deploy (Sprint 8). Em desenvolvimento local, sem um domínio público, o webhook exigiria um túnel adicional (ngrok ou similar) só para testar a vinculação. `getUpdates` com `timeout=0` funciona identicamente em qualquer ambiente, sem infraestrutura extra, ao custo de ser chamado sob demanda (a cada clique em "Verificar conexão") em vez de receber atualizações em tempo real — uma troca aceitável, já que a única atualização que o bot processa hoje é a confirmação de vinculação. Migrar para webhook no futuro não exigiria mudanças em `TelegramService`: apenas trocar como `TelegramClient` recebe as atualizações.

**Como o Celery entraria no futuro, sem mudar esta arquitetura:** `notify_task_overdue` (via `sync.notify_task`), `DailySummaryService.send_summary` e `WeeklySummaryService.send_summary` já existem e são testados; falta apenas *chamá-los* periodicamente. Uma tarefa periódica do Celery Beat (ex.: a cada hora, verificando tarefas com `due_date` no passado e `completed=False`) chamaria `sync.notify_task(task, TaskEvent.OVERDUE)` por tarefa vencida; outra (diária, ex. 8h) chamaria `DailySummaryService().send_summary(user)`; outra (semanal) chamaria `WeeklySummaryService().send_summary(user)`, por usuário conectado. Nenhuma delas precisaria conhecer `TelegramService` diretamente — o mesmo desacoplamento via `registry`/`notifications.py` que já existe hoje.

**Como o Redis entraria no futuro, sem mudar esta arquitetura:** Redis serviria a três papéis independentes, todos plugáveis sem alterar `CalendarEventProvider`/`NotificationProvider`: (1) *broker* do Celery, para as tarefas periódicas acima; (2) cache de estado, por exemplo armazenar o `offset` de `getUpdates` entre chamadas (resolvendo o débito técnico descrito abaixo) ou um contador simples para rate limiting local (evitar estourar o limite de ~30 mensagens/segundo da Bot API antes mesmo de tentar enviar); (3) *backend* compartilhado do throttling do DRF (`DEFAULT_THROTTLE_CLASSES`, ver "Decisões arquiteturais e trade-offs"). Hoje o contador de cada `AnonRateThrottle`/`UserRateThrottle` vive no `LocMemCache` — em memória, por processo — e com `GUNICORN_WORKERS=2` cada worker mantém sua própria contagem, então o limite efetivo por IP/usuário é, na prática, até `workers × taxa configurada`. Inofensivo para o propósito atual (frear automação simples, não impor um SLA exato), mas caso o limite precise ser exato entre workers, trocar `CACHES["default"]` para `django-redis` resolve sem tocar em nenhuma view, serializer ou permission — o throttling do DRF já é uma camada de cache, só falta um backend compartilhado.

## Limitações conhecidas

- **Escopo `calendar.events` é sensível para o Google** e exigiria um processo de verificação do app para uso público (vídeo demonstrativo, política de privacidade hospedada, revisão manual). Para este projeto — um case técnico, não um produto com usuários reais — o app permanece deliberadamente em modo **Testing**: funciona normalmente para até 100 usuários adicionados manualmente como **Test users** na tela de consentimento OAuth, sem o custo do processo de verificação. Isso é uma decisão consciente, não uma falha.
- **Sem fila de tarefas em segundo plano (Celery está fora do escopo)**: a sincronização com o Google Calendar é best-effort e síncrona. Uma falha de sincronização só é corrigida automaticamente na próxima operação sobre a mesma tarefa, não por um retry agendado.
- **Backoff de quota não implementado**: o cliente HTTP do Google Calendar tem retry de conexão e timeout configuráveis, mas não implementa o backoff exponencial documentado pelo Google para respostas `429`/`5xx` de limite de quota — o volume de uso de um projeto de demonstração não justifica essa complexidade agora, mas fica registrado como débito técnico caso o volume de sincronizações cresça.
- **Um único calendário por usuário** (`calendar_id`, padrão `"primary"`): não há UI para escolher entre múltiplos calendários da conta Google.
- **Polling em vez de webhook para o Telegram**: `getUpdates` é consultado sob demanda (ao clicar em "Verificar conexão"), não em tempo real. Ver "Performance" acima para a justificativa completa.
- **Sem offset persistente entre chamadas a `getUpdates`**: cada confirmação de vinculação reprocessa as atualizações recentes em vez de retomar de um ponto salvo — seguro (idempotente, filtrado por `linking_code` único), porém um pouco menos eficiente. Resolvido facilmente com Redis no futuro (ver "Performance").
- **Resumo diário, resumo semanal e notificação de tarefa vencida não são disparados automaticamente**: `DailySummaryService`, `WeeklySummaryService` e `notify_task_overdue` estão implementados e testados, mas não há Celery Beat, cron ou qualquer scheduler — por decisão explícita de escopo. Ver "Performance" para como essa peça se encaixaria no futuro sem mudar a arquitetura atual.
- **"Concluídas" no resumo semanal usa `updated_at`, não um `completed_at` dedicado**: `Task` não tem um campo próprio para registrar o instante da conclusão; `WeeklySummaryService` aproxima usando `updated_at` de tarefas com `completed=True`, o que pode incluir uma tarefa concluída há mais tempo mas editada nesta semana por outro motivo. Adicionar `completed_at` exigiria uma migration fora do escopo deste refinamento.
- **`task.shared_updated` dispara em qualquer atualização de uma tarefa compartilhada, não só em mudanças relevantes** (ex.: editar a descrição gera o mesmo aviso que mudar o prazo): mesmo nível de granularidade que `sync_task` já usa para o Google Calendar — refinar isso exigiria comparar campo a campo antes/depois, complexidade não justificada pelo volume de um projeto de demonstração.
- **Rate limit da Bot API não tratado de forma proativa**: o projeto não implementa throttling local para o limite de ~30 mensagens/segundo do Telegram — no volume de uso de uma demonstração, isso nunca é atingido, mas fica registrado como débito técnico caso o número de usuários conectados cresça.
- **Throttling do DRF impreciso entre workers**: o limite por IP/usuário (`DEFAULT_THROTTLE_RATES`) é contado em `LocMemCache`, em memória e por processo — com `GUNICORN_WORKERS=2`, o limite efetivo é até o dobro do configurado, já que cada worker conta separado. Aceitável para o propósito atual (frear automação simples), não para impor um SLA exato. Ver "Performance" para como Redis resolveria isso.

## Melhorias futuras

Itens deliberadamente fora do escopo das dez sprints entregues, candidatos a uma futura v2.0:

- **Fila de tarefas em segundo plano (Celery + Redis)**: dispararia `notify_task_overdue`, `DailySummaryService` e `WeeklySummaryService` automaticamente, e daria retry assíncrono às sincronizações com o Google Calendar. Ver "Performance" para como isso se encaixaria sem alterar a arquitetura atual.
- **Backend de cache compartilhado (Redis) para o throttling do DRF**: eliminaria a imprecisão de limite entre workers do Gunicorn (ver "Limitações conhecidas").
- **Webhook do Telegram em vez de polling**: reduziria a latência de confirmação de vinculação, viável agora que o projeto já tem HTTPS em produção.
- **Backoff exponencial para respostas `429`/`5xx` do Google Calendar**: hoje só há retry de conexão; o backoff de quota documentado pelo Google exigiria rodar fora do ciclo request/response (ligado à fila de tarefas acima).
- **Campo `completed_at` dedicado em `Task`**: substituiria a aproximação por `updated_at` no resumo semanal do Telegram.
- **Suporte a múltiplos calendários por usuário** na integração com o Google Calendar.
- **Observabilidade** (métricas, tracing, agregação de logs): os volumes de log já estão separados por serviço (ver "Arquitetura de produção"), prontos para receber um agente de coleta.
- **Autenticação social** (login via Google/GitHub) como alternativa ao cadastro por e-mail/senha.

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
| 7.1 | Generalização do canal de comunicação (refinamento arquitetural) | Concluído |
| 8 | Deploy completo na AWS (Free Tier) | Concluído |
| 9 | CI/CD (GitHub Actions, Selenium, releases) | Concluído |
| 10 | Refinamento de frontend (UI/UX) | Concluído |
| 10.1 | Refinamento de UX (validação inline, feedback de erro, estados vazios) | Concluído |
| 11 | Auditoria final, hardening, documentação definitiva e release `v1.0.0` | Em andamento |

> A Sprint 7.1 foi um refinamento arquitetural sobre o escopo já entregue na Sprint 7 (generalização do canal de comunicação, novos eventos de compartilhamento e sincronização, resumo semanal) — não altera a numeração nem o status das sprints acima.

> A Sprint 8 entrega toda a infraestrutura e documentação necessárias para publicar o projeto — Docker, Nginx, HTTPS, hardening e o guia completo em `docs/deploy-aws.md`. A execução prática na AWS (provisionar a EC2, seguir o guia) é feita por quem está avaliando o projeto, já que não há credenciais de nuvem compartilhadas nesta sessão.

> A Sprint 9 não adiciona nenhuma funcionalidade — o pipeline de CI (`.github/workflows/ci.yml`) roda em todo Pull Request para `develop`/`master`; a publicação de imagens (`publish.yml`) e o registro dos Environments (`deploy.yml`) rodam fora do PR; e `release.yml` só executa manualmente, quando alguém decidir cortar a primeira versão.

> A Sprint 11 também não adiciona nenhuma funcionalidade nova — é uma sprint de auditoria, hardening, documentação e preparação de release, sobre o escopo já entregue nas sprints anteriores.

## Como contribuir

Este é primariamente um projeto autoral, desenvolvido como case técnico — mas segue um fluxo de contribuição real, caso alguém queira propor uma mudança:

1. Abra uma branch a partir de `develop`, seguindo o padrão `feature/*`, `fix/*`, `refactor/*`, `docs/*` ou `test/*`.
2. Siga [Conventional Commits](https://www.conventionalcommits.org/) nas mensagens de commit.
3. Garanta que a suíte de testes passe localmente (`docker compose exec backend pytest`) e que build/lint do frontend estejam limpos (`npm run lint && npm run build`).
4. Abra um Pull Request contra `develop`, descrevendo o que mudou e por quê. O pipeline de CI (`ci.yml`) precisa passar antes do merge.
5. Nunca commit diretamente em `master` — merges para `master` só acontecem a partir de `develop`, após um conjunto estável e testado de funcionalidades.

## Autores

Desenvolvido por **Maria Leitão**.

## Licença

Este projeto está licenciado sob a licença MIT — veja o arquivo [`LICENSE`](LICENSE) para o texto completo. (Definida nesta sprint como padrão razoável para um projeto de portfólio open source; pode ser trocada a qualquer momento antes da publicação da release, caso outra licença seja preferida.)
