# Deploy em produção (AWS)

Guia completo, do zero, para publicar o Task Manager em uma instância EC2 gratuita (Free Tier), com HTTPS via Let's Encrypt. Assume que você nunca usou a AWS antes.

Arquitetura publicada:

```
Internet → Elastic IP → Nginx (80/443, TLS)
                          ├── /            → build estático do React
                          ├── /static/     → estáticos do Django (ex.: browsable API do DRF)
                          └── /api/        → proxy → Gunicorn
Gunicorn (backend) → PostgreSQL (container na rede interna, sem porta pública)
Gunicorn (backend) → Google Calendar API / Telegram Bot API
Certbot → renova o certificado Let's Encrypt automaticamente
```

Todos os serviços rodam em uma única instância EC2, via `docker-compose.prod.yml`. Ver README.md, seção "Arquitetura de produção", para a justificativa das escolhas.

## Índice

1. [Criar conta AWS e usuário IAM](#1-criar-conta-aws-e-usuário-iam)
2. [Criar a instância EC2](#2-criar-a-instância-ec2)
3. [Configurar o Security Group](#3-configurar-o-security-group)
4. [Alocar um Elastic IP](#4-alocar-um-elastic-ip)
5. [Configurar um domínio gratuito (DuckDNS)](#5-configurar-um-domínio-gratuito-duckdns)
6. [Acessar a instância via SSH](#6-acessar-a-instância-via-ssh)
7. [Instalar Docker e Docker Compose](#7-instalar-docker-e-docker-compose)
8. [Clonar o repositório e configurar o .env](#8-clonar-o-repositório-e-configurar-o-env)
9. [Subir a aplicação (HTTP, sem certificado ainda)](#9-subir-a-aplicação-http-sem-certificado-ainda)
10. [Emitir o certificado HTTPS (Certbot)](#10-emitir-o-certificado-https-certbot)
11. [Validar a aplicação em produção](#11-validar-a-aplicação-em-produção)
12. [Renovação do certificado](#12-renovação-do-certificado)
13. [Como atualizar a aplicação em produção](#13-como-atualizar-a-aplicação-em-produção)
14. [Rollback](#14-rollback)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Criar conta AWS e usuário IAM

1. Crie uma conta em [aws.amazon.com](https://aws.amazon.com) (exige cartão de crédito, mas os recursos usados aqui estão no Free Tier).
2. Não use o usuário root do dia a dia. Em **IAM → Users → Create user**, crie um usuário (ex.: `maria-deploy`) com a policy gerenciada `AdministratorAccess` (suficiente para um projeto pessoal; em um ambiente de equipe real, restrinja por serviço).
3. Gere um **access key** para esse usuário só se for usar a AWS CLI — para este guia, o console web já é suficiente.
4. Ative o **MFA** no usuário root e no usuário IAM (Security credentials → Assign MFA device).

## 2. Criar a instância EC2

1. **EC2 → Launch instance**.
2. Nome: `task-manager-prod`.
3. AMI: **Ubuntu Server 24.04 LTS** (free tier eligible).
4. Tipo de instância: **t3.micro** (1 vCPU, 1 GiB RAM — free tier; se sua conta só tiver t2.micro elegível, use t2.micro, o guia funciona igual).
5. Par de chaves: crie um novo (`task-manager-key`), formato `.pem`, e guarde o arquivo baixado — ele não pode ser baixado de novo depois.
6. Configurações de rede: deixe criar um novo Security Group (ajustamos no próximo passo).
7. Armazenamento: 20 GiB gp3 (dentro do free tier de 30 GiB de EBS).
8. **Launch instance**.

## 3. Configurar o Security Group

Edite o Security Group criado (**EC2 → Security Groups**) e garanta exatamente estas regras de entrada:

| Tipo | Porta | Origem |
|---|---|---|
| SSH | 22 | Seu IP (`meu IP`, não `0.0.0.0/0`) |
| HTTP | 80 | `0.0.0.0/0` |
| HTTPS | 443 | `0.0.0.0/0` |

Nenhuma outra porta deve estar aberta — em particular, **8000** (Gunicorn) e **5432** (Postgres) não são expostas publicamente; o `docker-compose.prod.yml` já não publica essas portas no host, então mesmo que o Security Group liberasse, nada estaria escutando nelas externamente. É defesa em profundidade.

## 4. Alocar um Elastic IP

Sem um Elastic IP, o IP público da instância muda a cada stop/start — o que quebraria o DNS e o certificado.

1. **EC2 → Elastic IPs → Allocate Elastic IP address**.
2. **Actions → Associate Elastic IP address** → selecione a instância `task-manager-prod`.
3. Anote o IP alocado (ex.: `54.90.12.34`).

Custo: gratuito enquanto associado a uma instância em execução. A AWS cobra apenas se o IP ficar alocado e **não associado** a nenhuma instância — não deixe Elastic IPs órfãos.

## 5. Configurar um domínio gratuito (DuckDNS)

Let's Encrypt não emite certificado para IP puro — é preciso um hostname.

1. Acesse [duckdns.org](https://www.duckdns.org) e faça login (GitHub/Google).
2. Crie um subdomínio, ex.: `task-manager-maria` → resultado: `task-manager-maria.duckdns.org`.
3. Aponte o campo IP para o Elastic IP do passo 4 e clique em **update ip**.
4. Confirme a propagação: `nslookup task-manager-maria.duckdns.org` deve retornar o Elastic IP.

Se no futuro você registrar um domínio próprio (Route 53, Registro.br etc.), basta criar um registro **A** apontando para o mesmo Elastic IP e trocar `DOMAIN_NAME` no `.env` — o restante do guia não muda.

## 6. Acessar a instância via SSH

```bash
chmod 400 task-manager-key.pem
ssh -i task-manager-key.pem ubuntu@<elastic-ip>
```

## 7. Instalar Docker e Docker Compose

Já dentro da instância:

```bash
sudo apt update && sudo apt upgrade -y

curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

# O plugin "docker compose" já vem incluso no script acima. Confirme:
docker compose version
```

## 8. Clonar o repositório e configurar o .env

```bash
git clone https://github.com/marialuizaleitao/task-manager.git
cd task-manager

cp .env.prod.example .env
nano .env
```

Preencha, no mínimo:

- `DJANGO_SECRET_KEY` — gere com `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`.
- `DOMAIN_NAME` / `DJANGO_ALLOWED_HOSTS` / `DJANGO_CSRF_TRUSTED_ORIGINS` — o hostname do passo 5.
- `POSTGRES_PASSWORD` — uma senha forte, gerada só para este ambiente.
- Credenciais de Google Calendar e Telegram, se for usar essas integrações em produção (ver README para como obtê-las; os redirect URIs precisam apontar para o domínio de produção, não `localhost`).

## 9. Subir a aplicação (HTTP, sem certificado ainda)

O Nginx de produção referencia um certificado que ainda não existe — subir a stack completa quebraria. O bootstrap usa um certificado autoassinado temporário só para o Nginx conseguir iniciar e servir o desafio ACME do Certbot:

```bash
DOMAIN=$(grep DOMAIN_NAME .env | cut -d '=' -f2)

# Certificado dummy, só para o Nginx subir.
docker compose -f docker-compose.prod.yml run --rm --entrypoint sh certbot -c "\
  mkdir -p /etc/letsencrypt/live/$DOMAIN && \
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout /etc/letsencrypt/live/$DOMAIN/privkey.pem \
    -out /etc/letsencrypt/live/$DOMAIN/fullchain.pem \
    -subj '/CN=localhost'"

docker compose -f docker-compose.prod.yml up -d --build
```

Confirme que os três serviços de aplicação estão de pé:

```bash
docker compose -f docker-compose.prod.yml ps
```

## 10. Emitir o certificado HTTPS (Certbot)

Com o Nginx já servindo `/.well-known/acme-challenge/` (mesmo com o certificado dummy), peça o certificado real:

```bash
docker compose -f docker-compose.prod.yml run --rm --entrypoint certbot certbot \
  certonly --webroot -w /var/www/certbot \
  -d $DOMAIN \
  --email seu-email@exemplo.com --agree-tos --no-eff-email --force-renewal

docker compose -f docker-compose.prod.yml restart nginx
```

O `certbot` sobrescreve os mesmos arquivos (`fullchain.pem`/`privkey.pem`) que o Nginx já referencia — só é preciso reiniciar o Nginx para ele carregar o certificado real em vez do dummy.

## 11. Validar a aplicação em produção

```bash
curl -I https://$DOMAIN/api/health/
```

Espera-se `HTTP/2 200`. Depois, pelo navegador:

- `https://<seu-domínio>` carrega o React, com cadeado válido.
- Cadastro/login funcionam (`/api/accounts/...`).
- CRUD de tarefas, categorias e compartilhamento funcionam.
- Se configurado, conectar Google Calendar e Telegram e confirmar que notificações chegam.

## 12. Renovação do certificado

O serviço `certbot` do `docker-compose.prod.yml` já roda em loop, verificando a cada 12h se o certificado está a menos de 30 dias do vencimento e renovando automaticamente — não é preciso nenhuma ação manual para a renovação em si.

O Nginx, porém, só relê o certificado ao reiniciar/recarregar. Adicione um cron no host para recarregar semanalmente (idempotente — não interrompe conexões em andamento):

```bash
crontab -e
```

```
0 3 * * 0 cd /home/ubuntu/task-manager && docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

## 13. Como atualizar a aplicação em produção

```bash
cd task-manager
git pull origin master
docker compose -f docker-compose.prod.yml up -d --build
```

O entrypoint do backend (`backend/docker-entrypoint.prod.sh`) já aplica migrations e recoleta estáticos automaticamente a cada subida — não há passo manual adicional.

## 14. Rollback

Se um deploy quebrar algo:

```bash
git log --oneline -5          # identifique o commit estável anterior
git checkout <commit-anterior>
docker compose -f docker-compose.prod.yml up -d --build
```

Migrations de banco não são revertidas automaticamente — se o deploy problemático incluiu uma migration destrutiva, ela precisa de uma migration reversa dedicada (`python manage.py migrate <app> <migration_anterior>`), não apenas do checkout do código. Para este projeto, nenhuma sprint até aqui introduziu migrations destrutivas (remoção de coluna/tabela com perda de dados), então o cenário mais provável de rollback é puramente de código.

Antes de repetir o deploy, sempre rode a suíte de testes localmente (`pytest` no backend) para confirmar que o commit de destino realmente está estável.

## 15. Troubleshooting

**`docker compose up` falha com "port is already allocated"** — outra coisa já usa 80/443 no host (ex.: um Nginx nativo do Ubuntu). Verifique com `sudo lsof -i :80` e pare o serviço concorrente.

**Nginx reinicia em loop (`docker compose logs nginx`)** — geralmente porque `DOMAIN_NAME` não bate com o `server_name` esperado, ou os arquivos de certificado não existem no caminho esperado (`/etc/letsencrypt/live/$DOMAIN/`). Confirme com `docker compose exec nginx ls /etc/letsencrypt/live/`.

**`502 Bad Gateway`** — o backend não está saudável. Veja `docker compose logs backend`; geralmente uma variável de ambiente faltando (`DJANGO_SECRET_KEY`, credenciais do Postgres) impede o Gunicorn de subir.

**Certificado não emite (`certbot` falha)** — confirme que a porta 80 está acessível externamente (`curl http://$DOMAIN/.well-known/acme-challenge/teste` de outra máquina) e que o DNS do DuckDNS já propagou (`nslookup $DOMAIN`).

**Browsable API do DRF carrega sem CSS** — `collectstatic` não rodou ou o volume `static_files` não está montado corretamente no Nginx. Confirme com `docker compose exec nginx ls /usr/share/nginx/html/backend-static/`.

**Instância fica sem memória (OOM) com todos os containers de pé** — t3.micro tem só 1 GiB de RAM. Se ocorrer, adicione um swapfile de 1 GiB:

```bash
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```
