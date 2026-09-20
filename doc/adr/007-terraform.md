# ADR-007: Terraform

## Status
Aceito

## Decisão
Terraform usa versão fixada no workflow, state remoto S3 versionado e ambientes isolados em `infra/terraform/envs/staging` e `production`. Plan/apply AWS ficam atrás de `AWS_DEPLOY_ENABLED` e OIDC.

## Consequências
O CI valida a infraestrutura sem credenciais AWS. Provisionamento real continua uma ação explícita e auditável.
