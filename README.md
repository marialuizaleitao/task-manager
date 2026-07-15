# Task Manager

Aplicação web de gerenciamento de tarefas (To-Do List), desenvolvida como case técnico para demonstrar práticas profissionais de engenharia de software: arquitetura em camadas, containerização, testes automatizados e CI/CD.

> **Status atual:** Sprint 5 concluída — autenticação (JWT), categorias, CRUD de tarefas, compartilhamento e busca/filtros/ordenação avançados funcionais no backend e no frontend.

## Tecnologias

**Backend**
- Python 3.13
- Django 5.2 (LTS) + Django REST Framework 3.17
- djangorestframework-simplejwt (autenticação JWT)
- django-filter (filtros combináveis via FilterSet)
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

## Estrutura de diretórios

```
task-manager/
├── backend/
│   ├── apps/
│   │   ├── accounts/       # Custom User, JWT, registro, login, /me
│   │   ├── categories/     # CRUD de categorias
│   │   ├── tasks/          # CRUD de tarefas, filtros (filters.py)
│   │   └── sharing/        # Compartilhamento de tarefas (TaskShare, permissions)
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

## Testes

```bash
docker compose exec backend pytest -v
```

## Roadmap

| Sprint | Escopo | Status |
|---|---|---|
| 0 | Estrutura inicial, Docker, configuração base | Concluído |
| 1 | Autenticação (JWT), cadastro e login | Concluído |
| 2 | Categorias | Concluído |
| 3 | CRUD de tarefas | Concluído |
| 4 | Compartilhamento de tarefas | Concluído |
| 5 | Busca, filtros avançados, ordenação e paginação | Concluído |
| 6 | Integração com API externa | Pendente |
| 7 | Frontend completo | Pendente |
| 8 | Testes e cobertura | Pendente |
| 9 | CI/CD | Pendente |
| 10 | Deploy na AWS | Pendente |
