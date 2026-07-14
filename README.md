# Task Manager

Aplicação web de gerenciamento de tarefas (To-Do List), desenvolvida como case técnico para demonstrar práticas profissionais de engenharia de software: arquitetura em camadas, containerização, testes automatizados e CI/CD.

> **Status atual:** Sprint 2 concluída — autenticação (JWT) e categorias funcionais no backend e no frontend.

## Tecnologias

**Backend**
- Python 3.13
- Django 5.2 (LTS) + Django REST Framework 3.17
- djangorestframework-simplejwt (autenticação JWT)
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

Regras de negócio ficam concentradas em services quando há lógica real a isolar (ex.: `accounts.services.register_user`). Módulos com CRUD simples e sem orquestração adicional (ex.: `categories`) resolvem tudo em serializer + viewset, sem um service artificial. Repositories são introduzidos apenas quando reduzem acoplamento de forma concreta — ainda não há necessidade real no projeto.

O frontend é organizado por responsabilidade (componentes, páginas, hooks, contextos e serviços de API), seguindo o mesmo princípio: cada pasta só existe quando há conteúdo real que a justifique.

## Estrutura de diretórios

```
task-manager/
├── backend/
│   ├── apps/
│   │   ├── accounts/       # Custom User, JWT, registro, login, /me
│   │   └── categories/     # CRUD de categorias
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
│   │   ├── components/     # CategoryForm, CategoryList, ProtectedRoute
│   │   ├── contexts/       # AuthContext / AuthProvider
│   │   ├── hooks/
│   │   ├── pages/          # LoginPage, RegisterPage, HomePage, CategoriesPage
│   │   ├── services/       # clientes de API (auth, categories, tokenStorage)
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

`pages/` (backend, futuras apps `tasks`/`sharing`) e componentes de frontend ainda não escritos continuam fora do repositório até existir conteúdo real — diretórios vazios não são versionados propositalmente.

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
| 3 | CRUD de tarefas | Pendente |
| 4 | Compartilhamento de tarefas | Pendente |
| 5 | Filtros, busca e paginação | Pendente |
| 6 | Integração com API externa | Pendente |
| 7 | Frontend completo | Pendente |
| 8 | Testes e cobertura | Pendente |
| 9 | CI/CD | Pendente |
| 10 | Deploy na AWS | Pendente |
