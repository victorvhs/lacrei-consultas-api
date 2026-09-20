# ADR-006: Registro de imagens

## Status
Aceito

## Decisão
O GHCR publica imagens imutáveis com `sha-<commit>`. ECR é o registro de execução AWS quando `AWS_DEPLOY_ENABLED=true`. A tag `latest` é apenas conveniência e não é usada para rollback.

## Consequências
O deploy é reproduzível e a versão pode ser rastreada ao commit de origem.
