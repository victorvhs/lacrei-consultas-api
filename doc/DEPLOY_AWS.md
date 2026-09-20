# Deploy AWS

## Estado atual

A infraestrutura AWS está versionada, mas não é mantida online continuamente. O deploy real exige `AWS_DEPLOY_ENABLED=true`, credenciais OIDC e aprovação do environment correspondente.

## Pré-requisitos

- Região definida: `sa-east-1`.
- Bucket S3 de bootstrap criado, versionado, criptografado e sem acesso público.
- OIDC configurado para o repositório e environments `staging`/`production`.
- Secrets Manager configurado para credenciais do banco e gateway.
- ECR criado com tags imutáveis e scan on push.

## Ordem de ativação

1. Aplicar `infra/terraform/bootstrap` com backend local temporário.
2. Inicializar e aplicar `infra/terraform/envs/shared`.
3. Aplicar staging e validar ALB, RDS, ECS e CloudWatch.
4. Configurar `AWS_DEPLOY_ENABLED=true` como variável do repositório/environment.
5. Fazer merge em `main` após staging aprovado.
6. Validar `/health/live`, `/health/ready` e smoke test.

## Desligamento

Desative a variável e destrua na ordem inversa: produção, staging, shared e bootstrap. Preserve snapshots e o state versionado até concluir a auditoria.
