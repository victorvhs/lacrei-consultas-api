# Diário de decisões

## 2026-09-20

- A SPEC-01 definiu Python 3.12, Django 5.2, PostgreSQL 16, Docker multi-stage, GitHub Actions e Terraform validado sem provisionamento contínuo.
- A SPEC-02 foi integrada em `dev` com CRUD de profissionais/consultas, JWT, probes, sanitização e 110 testes no CI.
- O gate de qualidade foi elevado para cobertura mínima de 95% no fluxo local.
- A SPEC-03 adicionou domínio de pagamentos, FakeGateway, AsaasGateway, outbox/inbox e workers.
- O CI foi reduzido por estágio: PR para `dev` executa lint/testes; `hml` executa build/deploy efêmero; produção exige aprovação.
- O ambiente local passou a respeitar variáveis exportadas antes do `.env`, evitando que o arquivo local sobrescreva configurações de CI.

## Uso de assistência

Ferramentas de IA foram usadas para acelerar busca, scaffolding e revisão. Código foi aceito somente após revisão, lint, testes, cobertura e validação no GitHub Actions.
