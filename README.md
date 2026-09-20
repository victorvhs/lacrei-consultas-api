# Lacrei Saúde API

API de Gerenciamento de Consultas Médicas — Lacrei Saúde.

## Quick Start

```bash
make setup
make up
```

Acesse http://localhost:8000/api/docs/

## Autenticação

```bash
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'
```

## Ambientes

| Ambiente | Porta | Descrição |
|----------|-------|-----------|
| dev | 8000 | Desenvolvimento com hot reload |
| staging local | 8001 | Release compose |

## CI/CD

- **main** → produção (deploy automático via GitHub Actions)
- **hml** → homologação (testes completos)
- **dev** → desenvolvimento (CI validação básica)

## Infraestrutura AWS

Código Terraform em `infra/terraform/`. Não provisionado — ver `doc/DEPLOY_AWS.md`.

## Rollback

```bash
make rollback ENV=staging TAG=sha-abc1234
```

## Uso de IA

Documentado em `doc/USO_DE_IA.md`.

## Stack

- Python 3.12, Django 5.2 LTS, DRF
- PostgreSQL 16
- Docker + Docker Compose
- GitHub Actions, Terraform
