1. Segurança e Autenticação

    Autenticação: djangorestframework-simplejwt (15 min access / 1 dia refresh).

    Autorização: IsAuthenticated global (exceto health checks e webhooks específicos).

    Sanitização (LGPD): IDs sempre UUID v4. Sanitização rigorosa (strip, Unicode NFC, anti-XSS). Nunca persistir dados sensíveis absolutos em logs.

    Rate Limiting: Throttle configurado no banco (User: 300/min, Anon: 20/min).

2. Modelos de Domínio
2.1 Profissional

    id (UUIDv4), nome_social (obrigatório, 2-150 chars), profissao (texto livre).

    logradouro, numero, complemento, bairro, cidade, uf, cep (armazenado apenas dígitos).

    email, telefone (validação de pelo menos um obrigatório - RN01).

    carteira_repasse_id (vinculado ao Asaas, retornado nas rotas).

2.2 Consulta

    id (UUIDv4), profissional_id (FK, on_delete=PROTECT).

    data_hora (ISO 8601, timezone America/Sao_Paulo).

    status (agendada, realizada, cancelada).

    valor (numeric 10,2, decimal > 0).

3. Regras de Negócio (RN)

    RN02: data_hora deve ser no futuro na criação.

    RN03: Bloqueio de consultas simultâneas ativas para o mesmo profissional.

    RN05: Proibido excluir profissional se houver consultas atreladas (erro 409).

    RN06: Transição de estado rígida (Cancelada/Realizada não voltam para Agendada).

4. Contrato da API (/api/v1/)

    Auth: POST /auth/token/, POST /auth/token/refresh/

    Profissionais: CRUD completo em /profissionais/ e /profissionais/{id}/

    Consultas: CRUD em /consultas/ com filtros por profissional_id, status e range de datas.

    Relacionamento: GET /profissionais/{id}/consultas/

    Erros: Formato padronizado único: {"error": {"code": "...", "message": "...", "details": {...}}}.

5. Testes (Core)

    Cobertura exigida: 85%.

    Utilização de APITestCase com PostgreSQL real configurado no Django.