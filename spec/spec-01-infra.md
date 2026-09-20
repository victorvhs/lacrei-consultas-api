SPEC 1 — Setup, Infraestrutura Cloud e CI/CD
1. Stack e Versões Base

    Linguagem: Python 3.12

    Framework: Django 5.2 LTS + Django REST Framework

    Gerenciador: Poetry 2.x

    Banco de Dados: PostgreSQL 16 (psycopg 3)

    Container: Docker multi-stage + Docker Compose

    CI/CD: GitHub Actions

    IaC: Terraform com versões fixadas (validação TFLint, Checkov)

    Nuvem Alvo: AWS (Fargate/EC2 - em revisão ADR-008)

2. Estrutura do Projeto

A estrutura base segue a organização por domínios e separação da infraestrutura:
Plaintext

├── .github/workflows/      # ci-cd.yml, infra.yml, rollback.yml
├── config/settings/        # base, local, test, production
├── core/                   # middlewares, paginação, mixins globais
├── infra/                  # terraform e módulos AWS
├── scripts/                # deploy_local.sh, smoke_test.sh
├── doc/                    # adr/, specs/, manuais
├── docker-compose.yml      # dev e perfil payments
├── docker-compose.release.yml # staging/produção locais

3. Ambientes e Imagem Docker (RC01-RC09)

    Imagem Única Multi-role: A mesma imagem executa a API (Gunicorn), os workers de fila e as migrações, controlada via CMD.

    Características Obrigatórias: FS somente leitura (/tmp liberado), usuário não-root (runAsNonRoot), graceful shutdown (SIGTERM tratado), logs restritos ao stdout/stderr.

    Probes: Endpoints /health/live e /health/ready implementados via middleware antes do ALLOWED_HOSTS.

    Migrações: Executadas como processo/container efêmero isolado, nunca no startup da API.

4. Infraestrutura AWS (Terraform)

    State Remoto: Bucket S3 versionado e com lock.

    Isolamento: Envs separadas para staging e production.

    Recursos: RDS PostgreSQL criptografado (privado), ALB em subnets públicas, ECS Fargate em subnets privadas, Secrets Manager para credenciais.

    CI/CD: Autenticação via OIDC no GitHub Actions.

5. CI/CD e Rollback

    Jobs CI (ci-cd.yml): Lint (Ruff, import-linter) → Testes (PostgreSQL, coverage) → Build (Trivy scan) → Deploy efêmero (compose local) → Publish (GHCR/ECR).

    Rollback: Suporte a rollback local (deploy_local.sh) por falha de health check e provisionamento de rollback via GitHub Actions e AWS Terraform state.

2. SPEC-02-CORE.md — Domínio Core e API de Agendamento

Foco: O coração do sistema. Gerenciamento de profissionais, horários, autenticação JWT e regras de segurança de dados (LGPD).