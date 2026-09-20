# Contributing — Lacrei Saúde API

## Setup

```bash
make setup
make up
```

Acesse http://localhost:8000/health/live

## Branches

| Branch | Ambiente |
|--------|----------|
| `main` | Produção |
| `hml` | Homologação |
| `dev` | Desenvolvimento |

## Fluxo

1. Crie uma branch `feature/<descricao>` a partir de `dev`
2. Desenvolva e escreva testes
3. Abra PR para `dev`
4. Após aprovação e CI verde, merge para `dev`
5. PR de `dev` → `hml` (bateria de testes completa)
6. PR de `hml` → `main` (produção)

## Commits

Conventional Commits:

```
feat: adiciona endpoint de pagadores
fix: corrige validação de CEP
refactor: extrai método de cálculo de repasse
test: adiciona teste de webhook duplicado
docs: atualiza ADR-008
```

## Testes

```bash
make lint
make test
make pre-push
```

Cobertura mínima: 95%.

Não faça push de uma feature sem executar `make pre-push`. Para testes de banco, o Docker Compose precisa estar ativo.

## Governança

- PRs devem usar Conventional Commits.
- Mudanças comportamentais devem atualizar a spec correspondente.
- Decisões arquiteturais entram em `doc/adr/`.
- Operação e incidentes entram em `doc/DIARIO.md` ou no runbook aplicável.
- Nunca incluir dados pessoais reais ou segredos em código, fixtures, logs ou prompts.

## PRs

Use o template em `.github/pull_request_template.md`.
