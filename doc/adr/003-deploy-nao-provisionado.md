# ADR-003: Deploy não provisionado

## Status
Aceito

## Contexto
O desafio exige deploy funcional, mas manter infra paga para teste voluntário não se justifica.

## Decisão
Terraform e pipelines completos, validados no CI, mas não provisionados. Ativados via flag `AWS_DEPLOY_ENABLED=true`.

## Consequências
CI prova que infra é válida; runbook documentado para ativar.
