# Changelog

Todas as mudanças notáveis deste projeto são documentadas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), e o
projeto adere a [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Unreleased]

Nada pendente além do que está descrito em "Melhorias futuras" no README.

## [1.0.0] - 2026-07-18

Primeira versão estável do projeto — cobre as onze sprints entregues, da
estrutura inicial à auditoria final e hardening de produção.

### Added

- Estrutura inicial do projeto, Docker e Docker Compose para desenvolvimento.
- Autenticação JWT, cadastro e login.
- CRUD de categorias.
- CRUD de tarefas.
- Compartilhamento de tarefas com controle de permissão (leitura/edição).
- Busca textual, filtros combináveis, ordenação e paginação.
- Integração com o Google Calendar (OAuth2, sincronização de eventos).
- Integração com o Telegram Bot API (notificações de tarefa).
- Canal de comunicação do sistema generalizado (`NotificationProvider`), com
  eventos de compartilhamento, sincronização com o Google Calendar e resumo
  semanal.
- Ambiente de produção e deploy na AWS: gateway Nginx único, HTTPS via Let's
  Encrypt/Certbot, hardening de segurança e performance, guia de deploy.
- Pipeline de integração contínua (GitHub Actions): testes de backend com
  cobertura, lint e build de frontend, suíte Selenium end-to-end, validação
  de build Docker e docker-compose.
- Dependabot para Python, Node e GitHub Actions.
- Publicação automática das imagens de backend e frontend no GitHub Container
  Registry.
- Preparação para GitHub Releases e Deployments (changelog, versionamento,
  workflow de release, environments documentados).
- Refinamento completo de UI/UX do frontend: paleta e tipografia unificadas,
  navegação compartilhada, validação inline de formulários, estados vazios e
  de erro consistentes em todas as telas.
- Rate limiting (`DEFAULT_THROTTLE_RATES`) para toda a API, protegendo contra
  força bruta e scraping simples.
- Teste de infraestrutura para o endpoint de health check (`config/test_views.py`).
- `LICENSE` (MIT).

### Changed

- Backend em produção passou a rodar como usuário não-root no container
  (`Dockerfile`, estágio `prod`).
- README reescrito por completo, no formato de projeto open source: visão
  geral, diagrama de arquitetura, decisões arquiteturais e trade-offs
  consolidados, guia de contribuição e licença.

### Fixed

- Título "Task Manager" ausente nas telas de login e cadastro.
- Campo "Sobrenome" estourando o layout no formulário de cadastro (bug de
  `flexbox`: input sem `width` combinado com label sem `min-width: 0`).
- Falha silenciosa no cadastro: erros de rede, 500 ou CORS não exibiam
  nenhuma mensagem ao usuário (`extractFieldErrors` agora sempre garante uma
  mensagem de fallback).
- `App.css` nunca era importado por `App.tsx` — todo o refinamento visual das
  sprints anteriores existia no código, mas nunca chegava a renderizar.
