# ADR-010: Camada anticorrupção de pagamentos

## Status
Aceito

## Decisão
O domínio de pagamentos usa `GatewayPagamento` e DTOs próprios. Apenas `payments.adaptadores.asaas` conhece o contrato Asaas. `FakeGateway` é o gateway padrão de desenvolvimento e CI.

## Consequências
Regras de negócio permanecem testáveis sem rede e a troca do gateway não altera a API de agendamento.
