# Rollback

## Local

```bash
make build APP_VERSION=sha-bad
make deploy TAG=sha-bad
./scripts/rollback_local.sh sha-good
```

O script valida `/health/live` e troca para a tag anterior quando a versão nova não fica saudável.

## AWS

1. Dispare `Rollback` em Actions.
2. Selecione `staging` ou `production`.
3. Informe uma tag `sha-<commit>` conhecida.
4. Aguarde a aprovação do environment.
5. Execute smoke test e confirme logs do serviço.

Antes de produção, restaure o snapshot RDS somente se houver evidência de dano de dados. Rollback de código não substitui plano de migração.
