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
```

Cobertura mínima: 85%

## PRs

Use o template em `.github/pull_request_template.md`.
