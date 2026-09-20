SPEC 3 — Módulo Financeiro (Integração Asaas)
1. Arquitetura Anticorrupção (Hexagonal/Ports & Adapters)

    O domínio da aplicação não conhece o Asaas.

    Contratos rígidos garantidos pelo import-linter (domínio não importa dependências externas).

    Porta: GatewayPagamento (Protocol) ditando funções como criar_cobranca(), solicitar_estorno().

    Adaptadores: AsaasGateway (httpx com timeouts explícitos) e FakeGateway (para testes locais e CI).

2. Modelos de Pagamento

    Pagador: Armazena dados do cliente (CPF apenas validado e descartado; persistido mascarado).

    Pagamento: FK para Consulta e Pagador. Estados controlados estritamente.

    Repasse: Define o percentual (split) e armazena a carteira_id estática do momento da transação.

    Mensageria (Tabelas PostgreSQL): OutboxMensagem (saída) e EventoRecebido (inbox/webhooks).

3. Regras de Pagamento (RP) e Máquina de Estados

    Cobranças exigem valor > 0 na Consulta.

    Apenas um pagamento ativo por consulta.

    Estados base: PENDENTE, CONFIRMADO, PAGO, VENCIDO, CANCELADO, ESTORNADO, etc.

    O estado só avança no banco após consulta direta à API do gateway (nunca confiando cegamente no payload do webhook).

4. Endpoints Financeiros

    POST /pagadores/ (Síncrono).

    POST /consultas/{id}/pagamentos/ (Assíncrono, grava outbox, retorna HTTP 202).

    GET /pagamentos/{id}/ e POST /pagamentos/{id}/estorno/.

    POST /webhooks/asaas/ (Webhook protegido por asaas-access-token, salva EventoRecebido).

5. Processamento Assíncrono (Workers e Cron)

    Sem Redis/Celery. Utilização de SKIP LOCKED do PostgreSQL no padrão Outbox/Inbox (ADR-011).

    processar_outbox: Envia chamadas de rede; trata retentativas via backoff exponencial.

    processar_eventos: Consome webhooks salvos, faz requisição reversa de confirmação e atualiza a máquina de estados.

    reconciliar_pagamentos: Worker agendado para capturar cobranças sem atualização ou webhooks perdidos.

6. Simulador e Resiliência

    Utilização do módulo asaas_simulator (um container Flask/Django secundário) para simular o comportamento do gateway e injetar cenários de caos (timeout, 500, webhooks fora de ordem) no pipeline.