# ADR-011: Outbox e inbox sem broker

## Status
Aceito

## Decisão
Outbox e inbox são tabelas PostgreSQL processadas com `select_for_update(skip_locked=True)`. A operação de negócio e a intenção de integração são persistidas na mesma transação.

## Consequências
Não há Redis, RabbitMQ ou SQS no desafio. A evolução para SQS será considerada se volume ou latência medidos ultrapassarem a capacidade do PostgreSQL.
