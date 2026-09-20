SPEC — API de Gerenciamento de Consultas Médicas (Lacrei Saúde)
Status: rascunho v0.4 · Local no repositório: doc/specs/SPEC.md (pasta doc/ listada no .dockerignore) · Origem: Desafio Técnico Back-end Lacrei Saúde (vaga voluntária de Tech Lead) · Prazo: 5 dias úteis

Modo de entrega: aplicação executada localmente em Docker; deploy para AWS pronto, versionado e validado no CI, mas não provisionado.

Cada requisito tem um ID (RF, RN, RS, RI, RC, RP, TP) para ser referenciado em issues, commits e testes. Itens [DECISÃO] são escolhas propostas e ainda sujeitas a revisão; itens [ABERTO] precisam ser fechados antes da fase correspondente.

Changelog
Versão	Mudança
v0.1	Deploy de staging e produção provisionados na AWS
v0.2	Sem nuvem: ambientes simulados localmente, AWS apenas como documento
v0.3	Terraform e pipeline AWS completos, validados no CI e desligados por flag; seção sobre uso de IA
v0.4	Integração com Asaas redesenhada com camada anticorrupção (porta, adaptadores, fake e simulador), outbox/inbox sem broker, máquina de estados de pagamento, matriz de modos de falha. Imagem pronta para orquestradores (liveness/readiness, migração separada, FS somente leitura). Kubernetes registrado como evolução fora do escopo (ADR-009). Correção: throttle com cache compartilhado. Caminhos docs/ → doc/. Escolha de computação AWS reaberta (Fargate × EC2 × Lambda)
1. Contexto e objetivo
A Lacrei Saúde conecta a comunidade LGBTQIAPN+ a profissionais de saúde com atendimento inclusivo. O desafio pede uma API RESTful de gerenciamento de consultas médicas com qualidade de produção, base para integrações futuras. O enunciado indica que a integração com o Asaas (split de pagamento) é onde a pessoa selecionada vai atuar, por isso ela recebe atenção especial nesta spec (seção 12).

Critério de sucesso:

Qualquer pessoa com Docker clona o repositório e faz a primeira requisição autenticada em menos de 10 minutos.
Pipeline no GitHub Actions executa lint → testes → build → deploy em ambiente efêmero a cada PR.
Staging e produção existem como código: terraform apply + AWS_DEPLOY_ENABLED=true colocam a API no ar sem alterar código.
Terraform validado no CI mesmo sem conta AWS.
Rollback demonstrado localmente e implementado para AWS.
Integração de pagamentos desacoplada do Asaas, resiliente às falhas documentadas pelo próprio Asaas e testada por cenários de falha.
Testes com APITestCase, README, ADRs e diário de decisões.
1.1 Escopo
Dentro do escopo	Fora do escopo
CRUD de profissionais e consultas; busca por profissional	Cadastro completo de pacientes, agenda, front-end, notificações
Autenticação, validação, CORS, logs	Provisionar recursos na AWS
Ambientes locais: dev, staging e produção em Docker	Manter qualquer ambiente online
Imagem pronta para ECS, EC2 ou Kubernetes	Cluster Kubernetes e canary deploy (ADR-009, demo opcional)
Terraform completo para staging e produção	Domínio e certificado reais
Workflows de deploy e rollback AWS (desligados)	
Bônus prioritário: pagamentos com camada anticorrupção, fake e adaptador Asaas (sandbox)	Transações reais; cartão de crédito, assinaturas, subcontas, notas fiscais, antecipação
Bônus: Swagger/Redoc	
1.2 Risco conhecido: critério de deploy
O enunciado lista "deploy funcional em staging e produção (AWS ou serviço equivalente)" como obrigatório. Por ser um processo voluntário, manter infraestrutura paga para um teste não se justifica.

Mitigação: decisão explícita no README e no ADR-003; CI provando que a infra é válida e que a imagem sobe e responde; jobs AWS visíveis como skipped com o motivo; runbook doc/DEPLOY_AWS.md para ativar.

1.3 Sensibilidade dos dados
Nome social vinculado a uma consulta de saúde é dado pessoal sensível (LGPD, art. 5º, II) e pode revelar identidade de gênero ou orientação sexual. Pagamentos adicionam CPF e dados financeiros. Consequências: IDs não sequenciais, nenhum dado pessoal em logs, acesso sempre autenticado, minimização (CPF completo não é persistido, seção 12.9), banco sem acesso público e criptografado na AWS, e apenas dados fictícios em seeds, testes, fixtures e prompts de ferramentas de IA.

2. Stack e versões
Camada	Tecnologia	Observação
Linguagem	Python 3.12	Obrigatório
Framework	Django 5.2 LTS + Django REST Framework	[DECISÃO] LTS pela janela de suporte
Dependências	Poetry 2.x	Obrigatório
Banco	PostgreSQL 16	Obrigatório
Driver	psycopg[binary] 3	
Autenticação	djangorestframework-simplejwt	[DECISÃO] ADR-002
CORS / filtros / config	django-cors-headers, django-filter, django-environ	
Estáticos	WhiteNoise	Swagger sem proxy e compatível com FS somente leitura
Cliente HTTP	httpx	Timeouts explícitos por fase; usado só no adaptador Asaas
Docs da API	drf-spectacular	Bônus
Servidor	Gunicorn (gthread)	
Qualidade Python	Ruff, coverage, pip-audit, import-linter	import-linter garante a fronteira do Asaas no CI
Testes	APITestCase (API), SimpleTestCase (domínio puro), respx (HTTP do adaptador)	
Simulador Asaas	Aplicação Python mínima em container próprio	[DECISÃO] seção 12.8
Container	Docker multi-stage + Docker Compose	Obrigatório
CI/CD	GitHub Actions	Obrigatório
Registro de imagens	GHCR e Amazon ECR	ADR-006
IaC	Terraform com versões fixadas	ADR-007
Qualidade IaC	terraform fmt, validate, TFLint, Checkov	
Nuvem alvo	AWS	[ABERTO] computação em revisão (ADR-008)
3. Modelo de domínio: agendamento
3.1 Diagrama
┌───────────────────────────┐         ┌──────────────────────────┐
│ Profissional              │ 1     N │ Consulta                 │
├───────────────────────────┤─────────├──────────────────────────┤
│ id: UUID (PK)             │         │ id: UUID (PK)            │
│ nome_social               │         │ profissional_id: FK      │
│ profissao                 │         │ data_hora                │
│ endereço (campos planos)  │         │ status                   │
│ email, telefone           │         │ valor (seção 12)         │
│ asaas_wallet_id (seção 12)│         │ criado_em, atualizado_em │
│ criado_em, atualizado_em  │         └──────────────────────────┘
└───────────────────────────┘
O modelo de pagamentos está na seção 12.4.

3.2 Profissional
Campo	Tipo	Obrigatório	Regras
id	UUID v4	auto	Somente leitura
nome_social	varchar(150)	sim	2–150 caracteres após strip; sem HTML
profissao	varchar(100)	sim	Texto livre normalizado [DECISÃO]
logradouro, numero, complemento, bairro, cidade	varchar	sim (exceto complemento)	numero texto para aceitar "s/n"
uf	char(2)	sim	Uma das 27 UFs
cep	char(8)	sim	Aceita com ou sem hífen; armazena só dígitos
email	varchar(254)	condicional	Normalizado para minúsculas
telefone	varchar(11)	condicional	10 ou 11 dígitos
carteira_repasse_id	varchar(64)	não	Identificador da carteira no gateway (walletId no Asaas); não é exposto com o nome do gateway na API
criado_em / atualizado_em	timestamptz	auto	
3.3 Consulta
Campo	Tipo	Obrigatório	Regras
id	UUID v4	auto	
profissional	FK	sim	on_delete=PROTECT
data_hora	timestamptz	sim	ISO 8601; USE_TZ=True, TIME_ZONE="America/Sao_Paulo"
status	varchar(20)	não	agendada, realizada, cancelada
valor	numeric(10,2)	não	Decimal, > 0 quando informado; obrigatório para gerar cobrança
criado_em / atualizado_em	timestamptz	auto	
3.4 Regras de negócio
ID	Regra	Violação
RN01	Profissional precisa de email ou telefone	400
RN02	data_hora no futuro ao criar consulta	400
RN03	Sem duas consultas não canceladas do mesmo profissional no mesmo horário	400
RN04	Consulta referencia profissional existente	400
RN05	Não excluir profissional com consultas	409
RN06	Consulta cancelada ou realizada não volta para agendada	400
RN07	Toda resposta é JSON	—
4. Contrato da API
Base: /api/v1/ · Formato: JSON · Autenticação: Authorization: Bearer <access_token>, exceto endpoints públicos.

4.1 Endpoints de agendamento e plataforma
ID	Método	Rota	Descrição	Sucesso
RF01	POST	/auth/token/	Par access/refresh (público, throttle)	200
RF02	POST	/auth/token/refresh/	Renova access token	200
RF03–RF07	GET/POST/GET/PUT·PATCH/DELETE	/profissionais/, /profissionais/{id}/	CRUD de profissionais (RN05 no DELETE)	200/201/204
RF08–RF12	GET/POST/GET/PUT·PATCH/DELETE	/consultas/, /consultas/{id}/	CRUD de consultas; filtros profissional_id, status, data_inicio, data_fim	200/201/204
RF13	GET	/profissionais/{id}/consultas/	Consultas do profissional (404 se não existir)	200
RF14a	GET	/health/live	Processo vivo + versão; não toca o banco (público, fora de /api/v1)	200
RF14b	GET	/health/ready	Pronto para tráfego: banco acessível (público, fora de /api/v1)	200 / 503
RF15	GET	/api/schema/, /api/docs/, /api/redoc/	OpenAPI, Swagger, Redoc	200
Endpoints de pagamento (RF16–RF22) estão na seção 12.6.

[DECISÃO] Liveness e readiness separados: se a liveness dependesse do banco, uma queda do PostgreSQL faria o orquestrador reiniciar todas as instâncias sem necessidade. Os dois endpoints são atendidos por middleware posicionado antes da validação de ALLOWED_HOSTS, porque health checks de ALB e Kubernetes chegam com o IP do container no header Host.

4.2 Exemplos
POST /api/v1/profissionais/

{
  "nome_social": "Ana Souza",
  "profissao": "Psicóloga",
  "logradouro": "Rua 10", "numero": "250", "complemento": "Sala 3",
  "bairro": "Setor Oeste", "cidade": "Goiânia", "uf": "GO", "cep": "74120-020",
  "email": "ana@example.com", "telefone": "(62) 99999-0000"
}
201 Created

{
  "id": "4b1f0c7e-2a4d-4c55-9a39-0d0f3f1e8a21",
  "nome_social": "Ana Souza",
  "profissao": "Psicóloga",
  "endereco": { "logradouro": "Rua 10", "numero": "250", "complemento": "Sala 3",
                "bairro": "Setor Oeste", "cidade": "Goiânia", "uf": "GO", "cep": "74120020" },
  "contato": { "email": "ana@example.com", "telefone": "62999990000" },
  "repasse_configurado": false,
  "criado_em": "2026-09-16T14:02:11-03:00",
  "atualizado_em": "2026-09-16T14:02:11-03:00"
}
POST /api/v1/consultas/

{ "profissional_id": "4b1f0c7e-…", "data_hora": "2026-10-01T15:00:00-03:00", "valor": "150.00" }
Escrita com campos planos, leitura agrupada; valores monetários como string decimal; listagens com select_related.

4.3 Paginação e erros
PageNumberPagination (page_size=20, máximo 100). Formato de erro único:

{ "error": { "code": "validation_error", "message": "Dados inválidos.",
             "details": { "cep": ["CEP deve conter 8 dígitos."] }, "request_id": "b7a1e0c2-…" } }
HTTP	code	Quando
400	validation_error / malformed_json	Payload ou filtro inválido
401	not_authenticated / token_invalid	Sem token ou token inválido
403	permission_denied	Sem permissão
404	not_found	Recurso ou rota inexistente
405	method_not_allowed	Método não suportado
409	conflict	RN05; pagamento ativo já existente (RP03)
415	unsupported_media_type	Content-Type diferente de JSON
422	business_rule_violation	Regra de pagamento violada (seção 12.5)
429	throttled	Limite excedido
500	internal_error	Erro inesperado
503	gateway_unavailable	Operação síncrona dependente do gateway indisponível (RF16)
5. Segurança da aplicação
ID	Requisito	Implementação	Verificação
RS01	Validação	Serializers + constraints no banco	Testes de erro
RS02	Sanitização	strip(), Unicode NFC, rejeita </> em texto livre, normalização de CEP/telefone/e-mail	Teste com <script>
RS03	SQL Injection	Só ORM; raw()/extra()/SQL com f-string bloqueados no CI; SKIP LOCKED via select_for_update(skip_locked=True)	Teste com ' OR 1=1 --
RS04	CORS	Allowlist por ambiente	Teste permitido/negado
RS05	Autenticação	JWT (15 min / 1 dia, rotação); IsAuthenticated global; webhook com autenticação própria (RS15)	401 em todos os protegidos
RS06	Log de acesso	JSON com request_id, rota, status, duração, user_id, environment, version	assertLogs
RS07	Log de erro	Stack trace só no log	Teste forçando 500
RS08	Privacidade nos logs	Nunca corpo, Authorization, access_token, asaas-access-token, CPF	Teste de ausência
RS09	Rate limiting	anon 20/min, user 300/min, auth 5/min, webhook 600/min. Correção v0.4: contadores em cache compartilhado (DatabaseCache) — com cache em memória local cada worker/réplica conta separadamente e o limite real se multiplica	Teste de 429
RS10	Hardening	DEBUG=False, SECRET_KEY obrigatória, ALLOWED_HOSTS restrito, flags HTTPS por env	check --deploy
RS11	Enumeração	UUID como chave pública	—
RS12	Dependências	pip-audit + Dependabot	CI
RS13	Container	Seção 8.2; Trivy na imagem	CI
RS14	Segredos	Só .example versionados; gitleaks	CI
RS15	Webhook	Seção 12.9	TP10–TP13
6. Estrutura do projeto
.
├── .github/
│   ├── workflows/{ci-cd.yml, infra.yml, rollback.yml}
│   ├── pull_request_template.md
│   └── dependabot.yml
├── config/settings/{base,local,test,production}.py
├── core/                          # health, middlewares, exception handler, paginação, mixins
├── profissionais/
├── consultas/
├── pagamentos/                    # seção 12.2
│   ├── dominio/                   # Python puro: estados, transições, regras de repasse, dinheiro, exceções
│   ├── portas.py                  # GatewayPagamento (Protocol) + DTOs
│   ├── aplicacao/                 # casos de uso
│   ├── adaptadores/
│   │   ├── asaas/                 # ÚNICO lugar que conhece o Asaas
│   │   └── fake.py
│   ├── models.py                  # Pagador, Pagamento, Repasse, OutboxMensagem, EventoRecebido
│   ├── api/                       # serializers, views, webhook
│   ├── management/commands/       # processar_outbox, processar_eventos, reconciliar_pagamentos, expurgar_eventos
│   └── tests/
├── asaas_simulator/               # container de testes (seção 12.8)
├── infra/
│   ├── terraform/{bootstrap, modules/*, envs/{shared,staging,production}}
│   ├── .tflint.hcl
│   └── ecs/task-definition.tpl.json
├── scripts/{deploy_local.sh, rollback_local.sh, smoke_test.sh, seed.py}
├── doc/
│   ├── specs/SPEC.md              # este documento
│   ├── adr/
│   ├── DEPLOY_AWS.md
│   ├── ROLLBACK.md
│   ├── ASAAS.md                   # modos de falha, diagramas de sequência, checklist de go-live
│   ├── USO_DE_IA.md
│   └── DIARIO.md
├── docker-compose.yml             # dev (perfil opcional `payments`: worker + simulador)
├── docker-compose.release.yml     # staging/produção locais
├── .importlinter                  # contratos de fronteira
├── .dockerignore                  # inclui doc/, infra/, .github/, asaas_simulator/, *.env
├── Dockerfile · Makefile · CONTRIBUTING.md · pyproject.toml · poetry.lock · README.md
7. Testes (agendamento e plataforma)
APITestCase com PostgreSQL real; cobertura mínima 85% no projeto todo. Testes de pagamentos estão na seção 12.12.

Área	Caso	Esperado
Profissionais	Criar válido; listar/filtrar; detalhar; PUT/PATCH	201/200
Detalhar inexistente	404
Excluir sem / com consultas	204 / 409
Campo obrigatório ausente; sem contato; CEP/UF/e-mail inválidos; <script>	400
Consultas	CRUD completo	201/200/204
Data no passado; horário duplicado; profissional inexistente/malformado; cancelada → agendada; valor ≤ 0	400
Mesmo horário, outro profissional	201
Busca	Rota aninhada filtra corretamente / profissional inexistente / filtro com UUID inválido	200 / 404 / 400
Segurança	Sem token ou token inválido	401
SQL injection em filtro e campo	Nunca 500
JSON malformado / Content-Type errado	400 / 415
CORS; throttle do token; rota inexistente	—; 429; 404 JSON
Logs	Acesso com request_id, sem dados pessoais	—
Health	live com banco fora; ready com banco fora; Host fora de ALLOWED_HOSTS	200; 503; 200
Performance básica	Listagens com número fixo de queries (assertNumQueries)	—
8. Ambientes e imagem
8.1 Ambientes
Ambiente	Onde	Banco	Imagem	Estado
dev	Compose, porta 8000	Container	Build local	Rodando
CI	Runner GitHub	Service container	Build do commit	A cada PR
staging local	Compose, porta 8001	Container próprio	sha-<commit>	Demonstração
produção local	Compose, porta 8002	Container próprio	sha-<commit>	Demonstração
staging AWS	Terraform	RDS	ECR	Código pronto, não provisionado
produção AWS	Terraform	RDS	ECR	Código pronto, não provisionado
8.2 Imagem pronta para orquestradores
A mesma imagem roda em Compose, ECS, EC2 ou como pod no Kubernetes, mudando apenas o comando e as variáveis.

ID	Requisito	Implementação
RC01	Um artefato, vários papéis	Mesma imagem executa api (Gunicorn), worker (processar_outbox/processar_eventos), migrate e reconciliar via comando
RC02	Probes	/health/live e /health/ready (RF14a/b)
RC03	Migração fora do startup	Nunca migrate no entrypoint da API; comando dedicado (Job no Kubernetes, run-task no ECS, container efêmero local) para evitar corrida entre réplicas
RC04	Desligamento gracioso	CMD em formato exec (Gunicorn recebe SIGTERM); graceful_timeout < prazo de término do orquestrador; workers terminam o item atual antes de sair
RC05	Usuário	Não-root com UID/GID numéricos (compatível com runAsNonRoot)
RC06	FS somente leitura	Nada gravado fora de /tmp; --worker-tmp-dir /dev/shm; estáticos coletados no build e servidos por WhiteNoise
RC07	Dimensionamento explícito	GUNICORN_WORKERS/GUNICORN_THREADS por env (contar CPUs dentro do container enxerga o host, não o limite)
RC08	Logs	Somente stdout/stderr em JSON
RC09	Sem estado local	Sessões, throttle e filas no banco; nenhuma dependência de disco ou memória entre requisições
[DECISÃO] ADR-009 — Kubernetes fora do escopo agora. Não é requisito, compete com itens obrigatórios, canary exige tráfego para ter valor e EKS tem custo fixo e curva de operação alta para times voluntários. RC01–RC09 garantem que a migração seja possível. Evolução documentada: deploy/k8s com kind + Argo Rollouts, canary com análise por health check e rollback automático, executado apenas se sobrar tempo.

8.3 Comandos locais (Makefile)
Comando	O que faz
make setup	Cria .env* a partir dos .example
make up / make down	Ambiente dev
make up-payments	Dev + worker + simulador Asaas (perfil payments)
make superuser / make seed	Usuário / dados fictícios
make lint / make test	Ruff + import-linter / testes com cobertura
make build	Imagem com APP_VERSION
make deploy ENV=… TAG=… / make rollback ENV=…	Deploy e rollback locais
make sim-pay PAGAMENTO=<id>	Simulador marca a cobrança como paga e dispara webhook
make sim-chaos CENARIO=duplicado|fora_de_ordem|timeout_apos_criar|erro_500	Configura falhas no simulador
make tf-check	Validações de Terraform sem credenciais
8.4 Variáveis de ambiente
Variável	Local	AWS
SECRET_KEY, senha do banco	.env	Secrets Manager
ALLOWED_HOSTS, CORS_ALLOWED_ORIGINS	.env	Task definition
SECURE_*	Desligados	Ligados com certificado
ENVIRONMENT, APP_VERSION, LOG_LEVEL, GUNICORN_WORKERS, GUNICORN_THREADS	.env / build	Task definition / build
PAYMENT_GATEWAY	fake (padrão), asaas	fake enquanto não houver conta
ASAAS_BASE_URL	URL do simulador ou do sandbox	URL do ambiente Asaas correspondente
ASAAS_API_KEY	Vazio ou chave do sandbox	Secrets Manager
ASAAS_WEBHOOK_TOKENS	Lista separada por vírgula (permite rotação)	Secrets Manager
REPASSE_PERCENTUAL_PADRAO	80	Task definition
9. Infraestrutura AWS como código
9.1 Arquitetura alvo
[ABERTO] ADR-008 — Computação. Em revisão entre ECS Fargate (menos operação, rollback nativo), EC2 com Compose (menor custo, mesmo mecanismo do deploy local) e Lambda com imagem de container (quase sem operação, mas exige cuidado com conexões ao RDS e rede em VPC). As seções abaixo descrevem Fargate como referência; os requisitos marcados com † mudam conforme a escolha.

GitHub Actions ──OIDC──► IAM Role por ambiente
      ├─► ECR (sha-<commit>, tags imutáveis)
      └─► Computação †  ── api ◄── ALB
                        ├─ worker (outbox + eventos)
                        └─ reconciliar (agendado)
               │ logs ► CloudWatch ► alarmes
               │ secrets ◄ Secrets Manager
               └ 5432 ► RDS PostgreSQL (privado, criptografado)
9.2 Requisitos de infraestrutura
ID	Requisito	Implementação
RI01	Ambientes isolados	envs/staging e envs/production com states e tags separados
RI02	State remoto seguro	Bucket S3 versionado, criptografado, sem acesso público, lock nativo
RI03 †	Rede	Subnets públicas (ALB) e privadas (computação e RDS); SGs encadeados
RI04 †	Custo controlável	enable_nat_gateway, contagem, CPU/memória, classe e multi-AZ do RDS por variável. Observação: o worker precisa sair para a internet (Asaas); sem NAT, a computação fica em subnet pública com SG restrito
RI05	Banco	RDS PostgreSQL 16, criptografado, privado, senha gerenciada no Secrets Manager, deletion_protection em produção
RI06	Registro	ECR com tags imutáveis, scan on push, lifecycle policy
RI07 †	API	Serviço com health check em /health/live, rollback automático por falha de deploy, autoscaling
RI08 †	Deploy sem drift	Revisões de deploy vêm do pipeline; Terraform ignora a revisão em uso
RI09	Acesso do CI	OIDC com trust restrito a repo e environment; permissões mínimas
RI10	Observabilidade	Log groups, alarmes de 5xx, targets unhealthy, CPU do RDS e métricas de pagamentos (seção 12.11)
RI11	HTTPS opcional	domain_name ativa ACM e listener 443
RI12	Qualidade	fmt, validate, TFLint, Checkov no CI
RI13	Custos	Principais geradores de custo e orientação de estimativa em DEPLOY_AWS.md
RI14 †	Processos de pagamento	Worker como serviço separado da API (escala independente, sem receber tráfego do ALB); reconciliação como tarefa agendada (EventBridge Scheduler)
9.3 Runbook de ativação
Bootstrap do state → envs/shared → staging → environments e variáveis no GitHub → AWS_DEPLOY_ENABLED=true → merge → produção → terraform destroy na ordem inversa para desligar. Detalhado em doc/DEPLOY_AWS.md, incluindo cadastro das chaves do Asaas no Secrets Manager e da URL do webhook na conta Asaas de cada ambiente.

10. CI/CD
10.1 ci-cd.yml
Job	Quando	Passos
lint	PR e push	Ruff; lint-imports (contratos da seção 12.2)
test	PR e push	Postgres; makemigrations --check; check --deploy; testes com cobertura ≥ 85%; pip-audit; gitleaks
build	PR e push	Imagem da API e do simulador; Trivy
deploy-ephemeral	PR e push	Compose de release no runner (API + worker + simulador); migração como passo separado; smoke_test.sh incluindo fluxo de pagamento ponta a ponta contra o simulador
publish	push em main	GHCR sha-<commit>
deploy-aws-staging	main + flag	OIDC → ECR → migração → API e worker → smoke test
deploy-aws-production	Após staging + flag + aprovação	Snapshot RDS → mesma imagem → migração → API e worker → smoke test
10.2 infra.yml
tf-check sempre em mudanças de infra/**; tf-plan e tf-apply só com a flag e aprovação.

10.3 Migrações
Antes da troca de versão, como passo separado (RC03), sempre expand/contract.

11. Rollback
Nível	Local (demonstrado)	AWS (implementado, não executado)
Automático	deploy_local.sh volta à versão anterior se /health/live não mostrar a versão nova	Rollback automático do serviço de computação †
Manual	make rollback ENV=…	rollback.yml com aprovação
Via Git	git revert + pipeline	git revert + pipeline
Banco	pg_dump antes do deploy	Snapshot RDS antes de produção
Infra	—	Reverter PR de Terraform; versionamento do state
Pagamentos	Outbox e eventos persistidos no banco sobrevivem ao rollback de código; nova e antiga versão precisam ler os mesmos formatos de mensagem (campo versao_payload na outbox)	Idem
Roteiro local: deploy sha-A → deploy sha-B quebrado com rollback automático → deploy sha-C e rollback manual para sha-A.

12. Integração de pagamentos com Asaas (bônus prioritário)
12.1 Objetivo e premissas
Demonstrar uma integração de split de pagamento pronta para evoluir para produção, com três propriedades verificáveis:

Desacoplamento: o domínio da Lacrei não conhece o Asaas; trocar ou simular o gateway não altera regras de negócio.
Resiliência: cada falha documentada pelo Asaas tem tratamento explícito e teste.
Segurança e LGPD: dados financeiros e pessoais minimizados e protegidos.
Premissas: nenhuma transação real; desenvolvimento e CI usam FakeGateway e o simulador; o adaptador real é validado manualmente contra o sandbox, se houver conta. [DECISÃO] Toda afirmação sobre o comportamento do Asaas nesta seção deve ser conferida na documentação oficial no início da implementação, e divergências registradas no DIARIO.md.

Fatos da documentação do Asaas que orientam o desenho:

Fato	Consequência no desenho
Split distribui o valor líquido da cobrança entre carteiras (walletId), em valor fixo ou percentual; soma limitada ao líquido ou a 100%	Repasse calculado e exibido como percentual do líquido; validação prévia de soma
A conta emissora não pode incluir a própria carteira no split	Validação no domínio
Estorno da cobrança estorna o split	Estorno atualiza repasses
Status de split: PENDING, AWAITING_CREDIT, CANCELLED, DONE, REFUSED (com motivo)	Estados de repasse (12.3)
Webhooks com entrega at least once; idempotência exigida	Inbox com event_id único (RP07)
Apenas HTTP 200 conta como sucesso na entrega do webhook (outra página cita faixa 2xx; divergência a registrar)	Webhook responde exatamente 200
Timeout de 10 s por entrega de webhook	Gravar e responder; processar de forma assíncrona
Retentativas progressivas; 15 falhas consecutivas pausam a fila; eventos com mais de 14 dias são descartados	Alerta de silêncio de webhook + reconciliação periódica
Token de autenticação obrigatório, enviado no header asaas-access-token; token estático não garante integridade nem protege contra replay	Comparação em tempo constante + confirmação do estado via API antes de agir
Polling repetido pode bloquear a chave por limite de cota	Webhook como fluxo principal; reconciliação espaçada e em lotes
Cobrança exige cliente cadastrado no Asaas	Entidade Pagador mínima (12.4)
Conta sandbox é independente da conta de produção	Chaves, carteiras e tokens separados por ambiente
12.2 Arquitetura: camada anticorrupção
[DECISÃO] ADR-010 — Portas e adaptadores na fronteira do gateway.

            ┌────────────────────────── pagamentos ──────────────────────────┐
 API ──────►│ api/ ──► aplicacao/ (casos de uso) ──► dominio/ (Python puro)   │
 (JWT)      │                 │                                                │
            │                 ▼                                                │
            │           portas.GatewayPagamento  ◄── contrato na língua Lacrei │
            │             ▲            ▲                                       │
            │   adaptadores/fake   adaptadores/asaas ── tradutor ── cliente HTTP ──► Asaas / simulador
            └──────────────────────────────────────────────────────────────────┘
 Asaas ──webhook──► api/webhook ──► EventoRecebido (inbox) ──► worker ──► aplicacao/
Regras de fronteira (verificadas por import-linter no CI):

Contrato	Descrição
C1	pagamentos.dominio não importa Django, httpx nem qualquer outro módulo de pagamentos
C2	Somente pagamentos.adaptadores.asaas pode referenciar o Asaas; nenhum outro módulo importa dele (a escolha é feita por uma fábrica que lê PAYMENT_GATEWAY)
C3	profissionais e consultas não importam pagamentos (a dependência é só no sentido pagamentos → agendamento)
[DECISÃO] Onde o desacoplamento para. A abstração cobre o gateway, que é externo, instável e trocável. Ela não cobre o ORM: casos de uso usam models Django diretamente, sem camada de repositório. Uma única porta com um adaptador real; nada de abstração genérica "multi-gateway". O nome do gateway aparece apenas no adaptador, na configuração e no campo gateway dos registros (auditoria).

Porta:

class GatewayPagamento(Protocol):
    def registrar_pagador(self, dados: DadosPagador) -> str: ...
    def criar_cobranca(self, pedido: PedidoCobranca) -> CobrancaGateway: ...
    def buscar_por_referencia(self, referencia: UUID) -> CobrancaGateway | None: ...
    def consultar_cobranca(self, id_externo: str) -> CobrancaGateway: ...
    def solicitar_estorno(self, id_externo: str) -> None: ...
    def autenticar_notificacao(self, headers: Mapping[str, str]) -> bool: ...
    def traduzir_notificacao(self, corpo: bytes) -> NotificacaoGateway: ...
DTOs são dataclass(frozen=True) com valores em Decimal e estados do domínio (nunca strings do Asaas). Exceções da porta:

Exceção	Significado	Retentável	Resultado da operação
GatewayIndisponivel	5xx, erro de conexão	Sim	Não realizada
ResultadoIncerto	Timeout de leitura após envio	Sim, após buscar_por_referencia	Desconhecido
LimiteDeRequisicoes	429	Sim, respeitando Retry-After	Não realizada
RequisicaoRecusada	4xx de negócio (carteira inválida, dados do pagador)	Não	Não realizada, com motivo traduzido
CobrancaNaoEncontrada	404	Não	—
CredencialInvalida	401/403	Não; alerta imediato	—
12.3 Linguagem do domínio e tradução
Estados de pagamento (domínio): AGUARDANDO_ENVIO, FALHA_ENVIO, PENDENTE, CONFIRMADO, PAGO, VENCIDO, CANCELADO, ESTORNO_EM_ANDAMENTO, ESTORNADO, EM_DISPUTA. Finais: CANCELADO, ESTORNADO.

Tradução no adaptador (lista a validar na documentação; status desconhecido não gera erro: mantém o estado, registra status_desconhecido e alerta):

Asaas	Domínio
PENDING, AWAITING_RISK_ANALYSIS	PENDENTE
CONFIRMED	CONFIRMADO
RECEIVED, RECEIVED_IN_CASH	PAGO
OVERDUE	VENCIDO
REFUND_REQUESTED, REFUND_IN_PROGRESS	ESTORNO_EM_ANDAMENTO
REFUNDED	ESTORNADO
CHARGEBACK_*, AWAITING_CHARGEBACK_REVERSAL	EM_DISPUTA
Evento de cobrança removida	CANCELADO
Transições permitidas:

AGUARDANDO_ENVIO ─► PENDENTE | FALHA_ENVIO
FALHA_ENVIO ─────► AGUARDANDO_ENVIO            (reprocessamento manual)
PENDENTE ────────► CONFIRMADO | PAGO | VENCIDO | CANCELADO
VENCIDO ─────────► PAGO | CANCELADO
CONFIRMADO ──────► PAGO | ESTORNO_EM_ANDAMENTO | EM_DISPUTA
PAGO ────────────► ESTORNO_EM_ANDAMENTO | ESTORNADO | EM_DISPUTA
ESTORNO_EM_ANDAMENTO ─► ESTORNADO
EM_DISPUTA ──────► PAGO | ESTORNADO
Regra de aplicação: o estado a aplicar vem sempre da consulta ao gateway, não do corpo do webhook. Se o estado consultado for alcançável a partir do atual pelo grafo (mesmo pulando etapas), é aplicado. Se for igual, nada muda. Se não for alcançável (regressão ou divergência), o pagamento não é alterado e é registrado divergencia_estado para revisão. Isso resolve eventos duplicados, fora de ordem e forjados com a mesma lógica.

Estados de repasse: PENDENTE, AGUARDANDO_CREDITO, CONCLUIDO, CANCELADO, RECUSADO (com motivo_recusa).

12.4 Modelo de dados
Consulta 1──N Pagamento N──1 Pagador
                 │ 1
                 └──N Repasse N──1 Profissional
OutboxMensagem   (fila de saída, referencia Pagamento)
EventoRecebido   (fila de entrada/inbox)
Modelo	Campos principais	Observações
Pagador	id, nome, documento_mascarado (***.***.***-12), email, id_externo, gateway, timestamps	CPF completo não é persistido: é validado, enviado ao gateway no cadastro síncrono e descartado
Pagamento	id (enviado como referência externa), consulta FK, pagador FK, valor Decimal, forma (PIX, BOLETO, ESCOLHA_DO_PAGADOR), vencimento, status, gateway, id_externo, url_pagamento, motivo_falha, versao (lock otimista), timestamps	Constraint: no máximo um pagamento não final por consulta
Repasse	pagamento FK, profissional FK, carteira_id (cópia no momento da cobrança), percentual, valor_estimado, status, motivo_recusa	A cópia da carteira preserva o histórico se o profissional trocar de conta
OutboxMensagem	id, tipo (CRIAR_COBRANCA, SOLICITAR_ESTORNO), pagamento FK, versao_payload, status (PENDENTE, PROCESSANDO, CONCLUIDA, FALHOU), tentativas, proxima_tentativa_em, ultimo_erro, timestamps	Índice parcial em (status, proxima_tentativa_em)
EventoRecebido	id, gateway, event_id (único por gateway), tipo, corpo JSON, status (RECEBIDO, PROCESSADO, IGNORADO, ERRO), tentativas, recebido_em, processado_em	Expurgo após 90 dias (expurgar_eventos)
Mudanças em modelos existentes: Profissional.carteira_repasse_id e Consulta.valor, ambos opcionais (migração expand).

12.5 Regras de pagamento
ID	Regra	Violação
RP01	Consulta precisa de valor > 0	422
RP02	Consulta cancelada não gera cobrança	422
RP03	No máximo um pagamento não final por consulta	409
RP04	Profissional precisa de carteira_repasse_id	422
RP05	Percentual de repasse entre 0 e 100, sobre o valor líquido; a carteira da conta emissora nunca entra no split	422
RP06	Dinheiro sempre Decimal com 2 casas; arredondamento ROUND_HALF_EVEN documentado	—
RP07	Evento do gateway processado no máximo uma vez (event_id único)	—
RP08	Estado só muda após confirmação no gateway (12.3)	—
RP09	Estorno apenas de pagamento CONFIRMADO ou PAGO	422
RP10	Pagamento PAGO não altera o status da consulta (fora do escopo; registrado como evolução)	—
12.6 Endpoints
ID	Método	Rota	Descrição	Sucesso
RF16	POST	/pagadores/	Cadastra pagador e registra no gateway de forma síncrona (retorna 503 se o gateway estiver indisponível)	201
RF17	GET	/pagadores/{id}/	Detalha com documento mascarado	200
RF18	POST	/consultas/{id}/pagamentos/	Solicita cobrança; grava pagamento + outbox na mesma transação	202
RF19	GET	/pagamentos/{id}/	Status, link de pagamento e repasses	200
RF20	GET	/consultas/{id}/pagamentos/	Histórico de pagamentos da consulta	200
RF21	POST	/pagamentos/{id}/estorno/	Solicita estorno via outbox	202
RF22	POST	/webhooks/asaas/	Recebe notificações (sem JWT; autenticação por token, RS15)	200
[DECISÃO] Pagador síncrono × cobrança assíncrona: o cadastro síncrono permite não persistir o CPF (minimização); a cobrança assíncrona garante que nenhuma intenção se perca e que a latência da API não dependa do gateway. O cliente acompanha pelo RF19, nunca consultando o Asaas diretamente.

Exemplo — RF18 → 202 Accepted

{
  "id": "0d9b3c1a-…",
  "status": "AGUARDANDO_ENVIO",
  "valor": "150.00",
  "forma": "PIX",
  "repasses": [ { "profissional_id": "4b1f0c7e-…", "percentual": "80.00", "status": "PENDENTE" } ],
  "links": { "self": "/api/v1/pagamentos/0d9b3c1a-…/" }
}
12.7 Fluxos
A. Criar cobrança (outbox)

Cliente ─POST RF18─► API: valida RP01–RP05 ─► TRANSAÇÃO { Pagamento AGUARDANDO_ENVIO + Repasses + OutboxMensagem } ─► 202
Worker processar_outbox (select_for_update skip_locked, lote):
  gateway.criar_cobranca(referencia = pagamento.id, split = repasses)
    ok ────────────────► id_externo, url, PENDENTE; mensagem CONCLUIDA
    ResultadoIncerto ──► buscar_por_referencia(pagamento.id): encontrou → trata como ok; não encontrou → reagenda
    GatewayIndisponivel/LimiteDeRequisicoes ─► reagenda com backoff exponencial + jitter (máx. 8 tentativas)
    RequisicaoRecusada ► FALHA_ENVIO com motivo; mensagem FALHOU; sem retentativa
    tentativas esgotadas ► FALHA_ENVIO + alerta
B. Receber webhook (inbox)

Asaas ─POST RF22─►
  1. Limite de tamanho do corpo (ex.: 256 KB) ─ excedido → 413
  2. autenticar_notificacao (compare_digest contra ASAAS_WEBHOOK_TOKENS) ─ falhou → 401 + log de segurança
  3. traduzir_notificacao ─ inválido → grava EventoRecebido ERRO, alerta, responde 200
  4. INSERT EventoRecebido ON CONFLICT (gateway, event_id) DO NOTHING
  5. Responde exatamente 200 {"recebido": true}   (alvo: < 200 ms)
[DECISÃO] Payload inválido com token válido responde 200: responder 4xx faria o Asaas retentar o mesmo evento até pausar a fila, prejudicando todos os eventos seguintes. O problema fica registrado e alertado do nosso lado.

C. Processar eventos

Worker processar_eventos (lote, skip_locked):
  localiza Pagamento por referência externa ou id_externo ─ não encontrado → IGNORADO
  tipo irrelevante (lista de interesse explícita) → IGNORADO
  cobranca = gateway.consultar_cobranca(id_externo)      ← fonte da verdade
  aplica transição (12.3) + atualiza repasses; evento PROCESSADO   (mesma transação)
  falha transitória → reagenda; esgotou → ERRO + alerta
D. Reconciliação (reconciliar_pagamentos, agendada; ex.: a cada 30 min)

Seleciona pagamentos não finais sem atualização há mais de X minutos, em lotes pequenos e espaçados; consulta o gateway; aplica transições; registra métrica pagamentos_corrigidos_por_reconciliacao. Também reenfileira mensagens PROCESSANDO travadas (worker que morreu) e emite alerta de silêncio se nenhum webhook chegou no período esperado com cobranças pendentes.

E. Estorno

RF21 valida RP09, grava outbox SOLICITAR_ESTORNO, worker chama o gateway, e o estado final chega por webhook/reconciliação; repasses passam para CANCELADO.

12.8 Implementações da porta
Implementação	Uso	Características
FakeGateway	Testes de domínio e de API; padrão em dev	Em memória, determinístico, permite programar respostas e exceções por chamada
AsaasGateway	Sandbox; produção no futuro	httpx com timeouts separados (conexão 3 s, leitura 10 s); header access_token; User-Agent identificando a aplicação; tradução completa de status, erros e payloads; logs com método, rota modelo, status e duração, sem chave nem CPF
Simulador (asaas_simulator/)	CI (deploy-ephemeral) e demonstração local	Container com subconjunto da API usado pelo adaptador (clientes, cobranças, busca por referência, estorno) e envio de webhooks com token. Endpoints de controle /_sim/*: marcar como paga, vencer, estornar, e falhas sob comando — webhook duplicado, fora de ordem, atraso, erro 500, 429, e timeout após criar (cria a cobrança e não responde)
[DECISÃO] Os payloads do simulador e dos testes do adaptador vêm do mesmo diretório de fixtures, gravados a partir da documentação ou do sandbox com dados fictícios. Assim o simulador não diverge do que o adaptador espera. Mudanças no formato do Asaas são corrigidas em um único lugar.

12.9 Segurança e LGPD
ID	Requisito	Implementação
RS15.1	Autenticação do webhook	hmac.compare_digest contra cada token de ASAAS_WEBHOOK_TOKENS; resposta 401 genérica
RS15.2	Rotação de token	Aceita dois tokens simultâneos durante a troca; procedimento em ASAAS.md
RS15.3	Anti-forja e anti-replay	Nenhum estado muda com base no corpo; sempre confirmação via API (RP08)
RS15.4	Exposição	Throttle webhook; limite de corpo; sem CORS; rota não listada no Swagger público
RS15.5	Credenciais	ASAAS_API_KEY só no adaptador, via env/Secrets Manager; chaves distintas por ambiente; CredencialInvalida gera alerta
RS15.6	Minimização	CPF validado (dígitos verificadores), enviado e descartado; apenas versão mascarada persistida e retornada
RS15.7	Retenção	EventoRecebido.corpo expurgado após 90 dias
RS15.8	Auditoria	Toda transição de pagamento gera log estruturado com pagamento_id, de, para, origem (webhook, reconciliacao, api), event_id
12.10 Matriz de modos de falha
#	Falha	Detecção	Tratamento	Teste
F01	Gateway fora do ar ao criar cobrança	GatewayIndisponivel	Backoff; após limite FALHA_ENVIO + alerta	TP04
F02	Timeout depois de a cobrança ser criada	ResultadoIncerto	buscar_por_referencia antes de retentar; nunca duplica	TP05
F03	Dados recusados (carteira, pagador)	RequisicaoRecusada	FALHA_ENVIO com motivo, sem retentativa	TP06
F04	Limite de requisições	LimiteDeRequisicoes	Respeita Retry-After; lotes menores	TP07
F05	Chave inválida ou revogada	CredencialInvalida	Para o worker de saída; alerta imediato	TP08
F06	Webhook duplicado	event_id repetido	ON CONFLICT DO NOTHING, 200	TP10
F07	Webhook fora de ordem	Estado consultado não alcançável	Ignora e registra divergência	TP11
F08	Webhook forjado	Token inválido ou estado não confirmado	401; ou nenhuma mudança	TP12, TP13
F09	Payload malformado com token válido	Falha na tradução	ERRO + alerta, responde 200	TP14
F10	Tipo de evento desconhecido	Fora da lista de interesse	IGNORADO	TP15
F11	Nosso endpoint fora do ar	Silêncio de webhooks	Retentativas do Asaas; reconciliação cobre; alerta antes de a fila pausar	TP17
F12	Fila pausada por mais de 14 dias	Silêncio prolongado	Reconciliação é a garantia final; runbook de reativação	Documentado
F13	Worker morre no meio do processamento	Mensagem PROCESSANDO antiga	Reconciliação reenfileira; operações idempotentes	TP18
F14	Split recusado	Status REFUSED	Repasse RECUSADO com motivo + alerta	TP16
F15	Profissional troca de carteira com cobrança em aberto	—	Repasse usa cópia da carteira do momento da cobrança	TP03
F16	Rollback de código com mensagens pendentes	versao_payload	Versões N e N-1 leem o mesmo formato (expand/contract)	Revisão
12.11 Observabilidade de pagamentos
Logs estruturados com pagamento_id, id_externo, event_id, mensagem_id (sem dados pessoais). Métricas expostas como contadores e gauges da aplicação (e, na AWS, filtros de métrica no CloudWatch):

Métrica	Alerta sugerido
outbox_idade_mensagem_mais_antiga_segundos	> 10 min
pagamentos_falha_envio_total	Qualquer aumento
eventos_recebidos_total{status}	ERRO > 0
segundos_desde_ultimo_webhook (com cobranças pendentes)	> 2 h
divergencias_estado_total	Qualquer aumento
gateway_requisicoes_total{operacao,resultado} e gateway_latencia_segundos	Taxa de erro > 5% em 5 min
pagamentos_corrigidos_por_reconciliacao_total	Aumento sustentado indica webhooks falhando
12.12 Testes de pagamentos
Camada	Ferramenta	Foco
Domínio	SimpleTestCase	Transições, alcançabilidade, cálculo de repasse, arredondamento, validação de CPF
Aplicação e API	APITestCase + FakeGateway	Endpoints, transações, outbox, inbox, workers executados de forma síncrona no teste
Adaptador	respx + fixtures	Tradução de status, erros HTTP → exceções, timeouts, headers, ausência de segredos no log
Integração	Simulador no deploy-ephemeral	Fluxo ponta a ponta e cenários de caos
Arquitetura	import-linter	Contratos C1–C3
ID	Caso
TP01	Criar cobrança válida → 202, pagamento + repasse + outbox na mesma transação
TP02	RP01–RP05 violadas → 422/409 com details
TP03	Repasse preserva a carteira do momento da cobrança
TP04	Gateway indisponível → reagendamento com backoff; limite → FALHA_ENVIO
TP05	Timeout após criação → busca por referência → uma única cobrança no gateway
TP06	4xx de negócio → FALHA_ENVIO com motivo, sem nova tentativa
TP07	429 respeita Retry-After
TP08	401 do gateway → alerta e parada do envio
TP09	Webhook válido → 200 exatamente, evento RECEBIDO
TP10	Webhook duplicado → 200, um único evento, uma única transição
TP11	Eventos fora de ordem → estado final correto, regressão ignorada
TP12	Token ausente ou inválido → 401, nada gravado
TP13	Token válido, corpo com status forjado → estado segue o consultado no gateway
TP14	Token válido, corpo malformado → 200, evento ERRO
TP15	Tipo de evento irrelevante → IGNORADO
TP16	Split recusado → repasse RECUSADO com motivo
TP17	Reconciliação corrige pagamento sem webhook
TP18	Mensagem PROCESSANDO abandonada é reenfileirada e processada sem duplicar
TP19	Estorno de pagamento pago → outbox → ESTORNADO, repasses CANCELADO; estorno de pendente → 422
TP20	CPF nunca aparece completo em banco, respostas ou logs
12.13 Escopo por fase
Fase	Itens
Essencial (dentro dos 5 dias)	Domínio e máquina de estados; porta, DTOs e exceções; FakeGateway; AsaasGateway com tradução e testes respx; models e migrações; RF16–RF22; outbox e inbox com workers; confirmação via API; TP01–TP16, TP19, TP20; import-linter; doc/ASAAS.md com a matriz 12.10 e diagramas de sequência
Se houver tempo	Simulador com caos no CI; reconciliação (TP17, TP18); métricas 12.11
Somente documentado	Circuit breaker; subcontas criadas pela Lacrei para profissionais; cartão de crédito; atualização do status da consulta ao pagar; checklist de go-live em produção
12.14 Questões em aberto de pagamentos
#	Questão	Padrão se não houver resposta
QP1	Quem paga: paciente, convênio, a própria Lacrei?	Paciente, representado por Pagador mínimo
QP2	Profissionais já têm conta Asaas ou a Lacrei cria subcontas?	Carteira informada manualmente; subcontas documentadas como evolução
QP3	Percentual de repasse global ou por profissional?	Global (REPASSE_PERCENTUAL_PADRAO), com campo por profissional como evolução
QP4	Taxas do Asaas: repasse sobre o líquido é o acordo com profissionais?	Sim, explicitado na resposta da API e no documento
QP5	Política de cancelamento, vencimento e estorno	Estorno manual via RF21; vencimento não cancela a consulta
QP6	Formas de pagamento	PIX e boleto; cartão fora do escopo
13. Documentação da API (bônus)
drf-spectacular com Swagger UI, Redoc e doc/openapi.yaml exportado; schema validado no CI; coleção Postman gerada do OpenAPI. Docs abertos no dev e autenticados nos demais ambientes. Endpoint de webhook fora do schema público.

14. Organização do trabalho (perspectiva de Tech Lead)
Prática	Artefato
Backlog rastreável	Issues com IDs desta spec, milestones por dia
Contribuição	CONTRIBUTING.md: setup, branches, Conventional Commits
Revisão	Template de PR: testes, expand/contract, sem dado pessoal em log, contratos de importação, Terraform revisado, spec atualizada
Proteção da main	CI e revisão obrigatórios
Decisões	ADRs curtos
Aprendizado	doc/DIARIO.md
Spec viva	Mudança de comportamento exige atualização desta spec no mesmo PR
Continuidade entre turmas	Runbooks, ADRs, infra como código, fronteira do gateway documentada
15. Uso de IA no desenvolvimento
A descrição do desafio e as diretrizes consultadas não restringem o uso de agentes de IA. [DECISÃO] Usar com transparência, como prática de engenharia documentada.

Diretriz	Como aplicar
Transparência	README e doc/USO_DE_IA.md indicam ferramentas e etapas
Responsabilidade	Propostas da IA são avaliadas, aceitas, alteradas ou rejeitadas; toda decisão final precisa ser explicável sem apoio
Verificação	Testes, cobertura, lint, contratos de importação, check --deploy, Checkov e smoke tests validam o que foi gerado
Fatos externos	Afirmações sobre serviços de terceiros (ex.: comportamento do Asaas) conferidas na documentação oficial
Dados	Nenhum segredo ou dado pessoal real em prompts
Registro	DIARIO.md anota onde a IA acelerou, onde errou e como foi corrigido
Commits	[ABERTO] Trailer Assisted-by: ou declaração só no documento
16. Documentação a entregar
Arquivo	Conteúdo mínimo
README.md	Execução local e infra não provisionada (com motivo); setup; token e curl; fluxo de pagamento com fake; testes; ambientes; CI/CD; rollback; uso de IA; links
doc/specs/SPEC.md	Este documento, mantido atualizado
doc/adr/	001 Stack · 002 JWT · 003 Deploy não provisionado · 004 Rollback · 005 Modelo de dados · 006 Registros · 007 Terraform · 008 Computação AWS · 009 Kubernetes fora do escopo · 010 Camada anticorrupção de pagamentos · 011 Outbox/inbox sem broker
doc/ASAAS.md	Fatos da documentação com links, arquitetura, diagramas de sequência (A–E), matriz de falhas, rotação de token, runbook de fila pausada, checklist de go-live
doc/DEPLOY_AWS.md · doc/ROLLBACK.md · doc/USO_DE_IA.md · doc/DIARIO.md	Conforme seções 9, 11, 15
CONTRIBUTING.md + template de PR	Seção 14
[DECISÃO] ADR-011 — Outbox/inbox sem broker. Filas no PostgreSQL com SKIP LOCKED evitam adicionar Redis, RabbitMQ ou SQS ao desafio, mantêm consistência transacional com os dados de negócio e bastam para o volume esperado. Evolução para SQS registrada com o gatilho de mudança (volume ou latência medidos).

17. Plano de execução (5 dias úteis)
Dia	Entregas	Pronto quando
1	Repositório, issues, Poetry, settings, Dockerfile com RC01–RC09, Compose, Makefile, modelos, health live/ready, Ruff	docker compose up --build responde
2	API de agendamento completa, JWT, CORS, throttle com cache compartilhado, erros, logs, sanitização; testes da seção 7	CRUDs via Swagger; testes verdes
3	CI (lint, test, build, deploy-ephemeral), Compose de release, deploy/rollback locais	CI verde; rollback local demonstrado
4	Pagamentos essencial (12.13): domínio, porta, fake, adaptador, models, endpoints, outbox/inbox, workers, testes, import-linter	TP essenciais verdes; fluxo com fake via curl
5	Terraform e jobs AWS atrás da flag; ASAAS.md e demais docs; clone limpo	Checklist completo; e-mail enviado
Ordem de corte: simulador → reconciliação e métricas → alarmes e autoscaling → ambiente production do Terraform (mantendo staging) → staging/produção locais (mantendo deploy efêmero). O essencial de pagamentos é cortado por último entre os bônus, por ser a área de atuação da vaga.

18. Checklist de aceite (Definition of Done)
Agendamento e plataforma

 RF01–RF15 e RN01–RN07 com testes
 RS01–RS14 verificados (incluindo throttle compartilhado)
 Cobertura ≥ 85% com APITestCase
Execução e entrega

 Clone limpo + docker compose up --build
 Imagem atende RC01–RC09
 CI com lint, testes, build e deploy efêmero verde
 Rollback local demonstrado
Infra AWS (pronta, não provisionada)

 ADR-008 fechado e RI01–RI14 coerentes com a escolha
 Checks de Terraform verdes; jobs AWS atrás da flag; runbook
Pagamentos

 Contratos C1–C3 verdes no CI
 RF16–RF22 e RP01–RP10 implementados
 TP essenciais verdes (12.13)
 CPF nunca persistido completo (TP20)
 doc/ASAAS.md com matriz de falhas e fatos conferidos na documentação oficial
Documentação

 README, ADRs 001–011, DEPLOY_AWS, ROLLBACK, USO_DE_IA, DIARIO, CONTRIBUTING
 Spec atualizada com o que mudou durante a implementação
 Repositório público enviado para desenvolvimento.humano@lacreisaude.com.br
19. Questões em aberto
#	Questão	Padrão se não houver resposta
Q1	A Lacrei aceita deploy pronto e não provisionado?	Seguir e justificar (ADR-003)
Q2	Região AWS	sa-east-1
Q3	Computação AWS: Fargate, EC2 ou Lambda	Em revisão (ADR-008)
Q4	profissao lista fechada ou texto livre	Texto livre
Q5	Exclusão de profissional com consultas	409
Q6	Marcação de commits assistidos por IA	Declarar em USO_DE_IA.md
QP1–QP6	Pagamentos	Seção 12.14