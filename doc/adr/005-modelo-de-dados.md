# ADR-005: Modelo de dados

## Status
Aceito

## Decisão
Profissionais e consultas usam UUID v4 como identificadores públicos. Consultas protegem a exclusão de profissionais. Pagamentos mantêm referências históricas de carteira e possuem constraint de um pagamento ativo por consulta.

## Consequências
O modelo reduz enumeração de recursos e preserva auditoria de repasses, mas exige filtros e fixtures que trabalhem com UUID.
