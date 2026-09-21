# ADR-008: Computação AWS

## Status
Em revisão

## Contexto
Fargate reduz operação, EC2 reduz custo unitário e Lambda reduz infraestrutura gerenciada, mas impõe restrições diferentes para workers e conexões PostgreSQL.

## Decisão provisória
Fargate permanece como arquitetura de referência: ALB público, serviços ECS em subnets privadas, worker separado e tarefa agendada de reconciliação.

## Próxima decisão
Fechar custo, operação e requisito de NAT antes de ativar `AWS_DEPLOY_ENABLED`.
