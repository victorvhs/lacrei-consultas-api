SPEC 4 — Governança, Qualidade e Processos
1. Contexto do Desafio

    Escopo: API RESTful robusta. Fora do escopo: front-end, notificações em tempo real, pagamentos reais, cluster Kubernetes (registrado como evolução futura).

    Restrição de Custo: Deploy AWS simulado/não provisionado constantemente (economia em conta pessoal), demonstrado via CI.

2. Padrões de Organização e Trabalho

    Commits: Conventional Commits (validado em PR).

    Branches e Revisão: Proteção da branch main, exigência de PRs com CI verde.

    Registro de Decisões: Manutenção rigorosa da pasta doc/adr/ (Architecture Decision Records) e do DIARIO.md.

3. Uso de IA Assistiva

    Transparência documentada em USO_DE_IA.md.

    Toda geração de código passa por crivo rigoroso do desenvolvedor, testes e verificações estáticas (Checkov, pip-audit, Trivy).

    Vedada a utilização de dados reais (LGPD) ou credenciais em prompts.

4. Documentação da API

    Integração nativa com drf-spectacular gerando Swagger UI, Redoc e schema exportável em doc/openapi.yaml.

    Endpoint de webhooks (/webhooks/asaas/) deve ser suprimido da documentação pública.

5. Cronograma e Execução (Plano de 5 dias)

    Dia 1: Repositório, Models, Setup Docker, Makefile, Probes.

    Dia 2: API Core (Auth, CRUD, Throttle, Regras de Agendamento).

    Dia 3: CI/CD Completo, Docker Compose Local, Teste de Rollback.

    Dia 4: Pagamentos (Essencial) - Domínio, Anticorrupção, Models, Workers Outbox/Inbox.

    Dia 5: Terraform (behind feature flag), Documentação Asaas, Revisão Final.

6. Definition of Done (Checklist de Aceite)

    [x] Execução limpa de docker compose up --build.

    [x] Pipeline por estágio com Lint, Testes, Build e Deploy Efêmero.

    [x] AWS Infra pronta em código (Terraform checked).

    [x] Rollback manual/local documentado e scriptado.

    [x] Regras de Integração de Pagamento com desacoplamento provado (Fake vs Asaas).

    [x] Nenhuma persistência completa de CPFs em base de dados (apenas sanitizado/mascarado).

    [x] ADRs, specs e README redigidos e atualizados.
