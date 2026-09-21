# Integração Asaas

## Fronteira

O único módulo que conhece o contrato Asaas é `payments.adaptadores.asaas.gateway.AsaasGateway`. O domínio usa estados e exceções próprios. CI e desenvolvimento usam `FakeGateway`.

## Segurança

- `ASAAS_API_KEY` só existe no adaptador e em Secret Manager.
- Webhook usa `asaas-access-token` comparado com `hmac.compare_digest`.
- CPF é validado, enviado ao gateway e descartado; somente máscara é persistida.
- Webhook válido responde HTTP 200 e é persistido na inbox.
- Estado do pagamento é confirmado consultando o gateway antes de aplicar transição.

## Falhas

| Falha | Tratamento |
|---|---|
| Timeout após envio | Busca por referência antes de repetir |
| 5xx/conexão | Backoff exponencial com limite de tentativas |
| 429 | Reagendamento e redução de lote |
| 4xx de negócio | Falha definitiva com motivo |
| Webhook duplicado | Constraint `(gateway, event_id)` |
| Webhook fora de ordem | Estado não alcançável é registrado como divergência |
| Payload inválido autenticado | Evento ERRO e resposta 200 |

## Workers

```bash
python manage.py processar_outbox
python manage.py processar_eventos
python manage.py reconciliar_pagamentos
python manage.py expurgar_eventos --dias 90
```
