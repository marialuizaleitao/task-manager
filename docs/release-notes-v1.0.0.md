# Release v1.0.0 (rascunho — não publicada)

Este documento é o rascunho da primeira Release do projeto, preparado na Sprint 11.
**Nenhuma tag ou Release foi criada no GitHub** — a publicação é uma decisão que
cabe a quem mantém o repositório. O conteúdo abaixo pode ser copiado diretamente
para o campo de descrição ao criar a Release manualmente, ou usado como entrada
para o workflow `.github/workflows/release.yml` (`workflow_dispatch`).

**Tag sugerida:** `v1.0.0`
**Branch de origem:** `master` (após o merge de `develop`)

---

## Task Manager v1.0.0

Primeira versão estável do projeto: uma aplicação completa de gerenciamento de
tarefas construída como case técnico, cobrindo autenticação, CRUD completo,
compartilhamento com controle de permissão, busca/filtros/ordenação, duas
integrações externas (Google Calendar e Telegram), deploy em produção na AWS
e um pipeline de CI/CD completo.

### Principais funcionalidades

- **Autenticação JWT** — cadastro, login, refresh e logout com blacklist de token.
- **CRUD de tarefas e categorias**, com validação de domínio e paginação.
- **Compartilhamento de tarefas** com dois níveis de permissão (leitura/edição),
  autorização decidida em duas camadas (visibilidade via `get_queryset`,
  permissão via `TaskAccessPermission`).
- **Busca, filtros combináveis e ordenação** sobre tarefas próprias e
  compartilhadas, com índices compostos dedicados no banco.
- **Integração com o Google Calendar** — OAuth2 completo (Authorization Code
  Flow), sincronização best-effort de eventos, nunca bloqueante para o usuário.
- **Canal de comunicação via Telegram** — vinculação por deep link, notificações
  de criação/conclusão/compartilhamento, resumos diário e semanal.
- **Interface React** refinada (paleta e tipografia unificadas, validação
  inline, estados vazios e de erro consistentes).

### Infraestrutura e qualidade

- Docker Compose para desenvolvimento e produção, com imagens dedicadas por
  ambiente (`dev`/`prod`) para backend e frontend.
- Deploy em produção na AWS (EC2 Free Tier), com Nginx como gateway único,
  HTTPS via Let's Encrypt/Certbot e hardening de segurança (HSTS, cookies
  seguros, container backend rodando como usuário não-root, rate limiting por
  IP/usuário).
- Pipeline de CI/CD no GitHub Actions: testes com cobertura, lint e build de
  frontend, suíte Selenium end-to-end, validação de build Docker, publicação
  automática de imagens no GitHub Container Registry e Dependabot.
- 265 testes automatizados, 98% de cobertura de código no backend.

### Tecnologias

Python 3.13 · Django 5.2 · Django REST Framework · djangorestframework-simplejwt
· django-filter · httpx · cryptography (Fernet) · PostgreSQL 18 · React 19 ·
TypeScript · React Router · Vite · Docker · Docker Compose · Nginx · Let's
Encrypt/Certbot · AWS EC2 · Gunicorn · GitHub Actions · GitHub Container
Registry · Dependabot · Selenium · pytest / pytest-cov

### Estatísticas do projeto

| Métrica | Valor |
|---|---|
| Testes automatizados (backend) | 265 |
| Cobertura de testes (backend) | 98% |
| Suítes end-to-end (Selenium) | 2 (fluxo de autenticação, ciclo de vida de tarefa) |
| Workflows de CI/CD (GitHub Actions) | 4 (`ci`, `publish`, `release`, `deploy`) |
| Integrações externas | 2 (Google Calendar, Telegram) |
| Imagens Docker | 4 (backend `dev`/`prod`, frontend `dev`/`prod`) |
| Apps Django | 7 (`accounts`, `categories`, `tasks`, `sharing`, `integrations`, `integrations.google_calendar`, `integrations.telegram`) |
| Endpoints de API | 24 |
| Linhas de código (aproximado) | ~8.300 (backend ~5.960, frontend ~2.140, e2e ~190) |
| Sprints entregues | 11 (0 a 11, incluindo o refinamento 7.1) |

### Resumo das sprints entregues

| Sprint | Entrega |
|---|---|
| 0 | Estrutura inicial, Docker, configuração base |
| 1 | Autenticação JWT, cadastro e login |
| 2 | CRUD de categorias |
| 3 | CRUD de tarefas |
| 4 | Compartilhamento de tarefas com controle de permissão |
| 5 | Busca, filtros avançados, ordenação e paginação |
| 6 | Integração com o Google Calendar (OAuth2) |
| 7 | Integração com o Telegram Bot API |
| 7.1 | Generalização do canal de comunicação (`NotificationProvider`) |
| 8 | Deploy completo na AWS (Free Tier) |
| 9 | CI/CD completo (GitHub Actions, Selenium, Dependabot, releases) |
| 10 | Refinamento de frontend (UI/UX) |
| 10.1 | Refinamento de UX (validação, feedback, estados vazios) |
| 11 | Auditoria final, hardening, documentação definitiva e esta release |

### Notas de hardening desta versão

- Container de backend em produção passou a rodar como usuário não-root.
- Rate limiting (`DEFAULT_THROTTLE_RATES`) adicionado a toda a API.
- Cobertura de testes ampliada (endpoint de health check antes sem teste).
- Documentação consolidada em um README único, no padrão de projeto open
  source, incluindo diagrama de arquitetura, decisões e trade-offs, e um
  roadmap de melhorias futuras.

### Débitos técnicos conhecidos

Nenhum bloqueante. Documentados em detalhe no README, seções "Limitações
conhecidas" e "Melhorias futuras": ausência de fila de tarefas em segundo
plano (Celery), throttling impreciso entre workers do Gunicorn sem Redis, e
a rota `/admin/` exposta sem nenhum model registrado.
