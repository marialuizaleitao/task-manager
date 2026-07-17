# Changelog

Todas as mudanças notáveis deste projeto são documentadas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), e o
projeto adere a [Versionamento Semântico](https://semver.org/lang/pt-BR/).
Nenhuma versão foi publicada ainda — tudo abaixo está em `Unreleased`.

## [Unreleased]

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
