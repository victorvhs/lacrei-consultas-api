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

Pull requests para `dev` executam lint e testes. Pull requests para `hml` também executam build, Trivy e deploy efêmero. Runs antigos da mesma branch são cancelados automaticamente.

## Infraestrutura AWS

Código Terraform em `infra/terraform/`. Não provisionado — ver `doc/DEPLOY_AWS.md`.

## Rollback

```bash
make rollback ENV=staging TAG=sha-abc1234
```

Runbook completo: [`doc/ROLLBACK.md`](doc/ROLLBACK.md).

## Qualidade local

```bash
make pre-push
```

O comando executa Ruff, import-linter, testes PostgreSQL e cobertura mínima de 95%. O CI deve confirmar o mesmo resultado antes do merge.

## Documentação

- OpenAPI: [`doc/openapi.yaml`](doc/openapi.yaml)
- Deploy AWS: [`doc/DEPLOY_AWS.md`](doc/DEPLOY_AWS.md)
- Pagamentos/Asaas: [`doc/ASAAS.md`](doc/ASAAS.md)
- Rollback: [`doc/ROLLBACK.md`](doc/ROLLBACK.md)
- ADRs: [`doc/adr/`](doc/adr/)
- Diário: [`doc/DIARIO.md`](doc/DIARIO.md)
- Uso de IA: [`doc/USO_DE_IA.md`](doc/USO_DE_IA.md)

## Uso de IA

Documentado em `doc/USO_DE_IA.md`.

## Stack

- Python 3.12, Django 5.2 LTS, DRF
- PostgreSQL 16
- Docker + Docker Compose
- GitHub Actions, Terraform
